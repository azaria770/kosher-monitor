import os
import requests
import pandas as pd
import time

def get_top_kosher_fund():
    # ה-ID החדש והמעודכן ביותר של מאגר קרנות נאמנות - מחירים
    resource_id = "8555776d-068d-4861-bcc5-c266a8779951"
    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}&limit=5000"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # פנייה ל-API עם מזהה המשאב החדש
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if not data.get('success'):
            print(f"API Error with new ID: {data.get('error')}")
            return None
            
        records = data['result']['records']
        df = pd.DataFrame(records)
        
        # איתור עמודות (גמיש לשמות שונים)
        col_name = next((c for c in df.columns if 'FUND_NAME' in str(c).upper() or 'שם' in str(c)), None)
        col_yield = next((c for c in df.columns if 'YIELD' in str(c).upper() or 'תשואה' in str(c)), None)
        col_fee = next((c for c in df.columns if 'FEE' in str(c).upper() or 'ניהול' in str(c) or 'שכ"נ' in str(c)), None)

        # סינון קרנות כספיות כשרות
        # הוספתי הגנה למקרה שהעמודה ריקה
        mask = (df[col_name].str.contains('כספית', na=False)) & \
               (df[col_name].str.contains('כשר', na=False))
        
        kosher_df = df[mask].copy()

        if kosher_df.empty:
            print("Filtering logic: No funds matched 'כספית' and 'כשר'.")
            return None

        # המרה למספרים וחישוב
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        
        # חישוב תשואה נטו
        kosher_df['NET_PROFIT'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        # מציאת המנצחת
        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET_PROFIT': winner['NET_PROFIT'],
            'MANAGEMENT_FEE': winner[col_fee]
        }

    except Exception as e:
        print(f"Connection/Processing error: {e}")
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
        print("Success! Message sent to Telegram.")
    else:
        print("Process ended without data.")
