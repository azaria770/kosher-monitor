import os
import requests
import pandas as pd
import time

def get_top_kosher_fund():
    # שימוש ב-API במקום הורדת קובץ ישירה לעקיפת חסימת ה-JS
    url = "https://data.gov.il/api/3/action/datastore_search"
    resource_id = "633db711-a3f3-469c-a6fd-059e09d82998"
    
    params = {
        'resource_id': resource_id,
        'limit': 2000,
        '_': int(time.time()) # פרמטר למניעת מטמון (Cache busting)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        data = response.json()
        
        if 'result' not in data:
            print("API response error:", data)
            return None
            
        records = data['result']['records']
        df = pd.DataFrame(records)
        
        # איתור עמודות חכם
        col_name = next((c for c in df.columns if 'NAME' in c.upper() or 'שם' in c), None)
        col_yield = next((c for c in df.columns if 'YIELD_DAILY' in c.upper() or 'תשואה' in c), None)
        col_fee = next((c for c in df.columns if 'MANAGEMENT_FEE' in c.upper() or 'ניהול' in c or 'שכ"נ' in c), None)

        # סינון קרנות כספיות כשרות
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר', na=False))
        ].copy()

        if kosher_df.empty:
            print("No funds matched filters.")
            return None

        # ניקוי נתונים וחישוב נטו
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        kosher_df['NET_PROFIT'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET_PROFIT': winner['NET_PROFIT'],
            'MANAGEMENT_FEE': winner[col_fee]
        }

    except Exception as e:
        print(f"Final check error: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET_PROFIT']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['MANAGEMENT_FEE']}%` \n"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    winner_data = get_top_kosher_fund()
    if winner_data:
        send_to_telegram(winner_data)
