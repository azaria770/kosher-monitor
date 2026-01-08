import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    csv_url = "https://data.gov.il/dataset/e6fce050-705d-4f05-9502-0e23805494d9/resource/633db711-a3f3-469c-a6fd-059e09d82998/download/funds.csv"
    
    # הגדרת "זהות" של דפדפן רגיל כדי לעקוף חסימות
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # הורדת התוכן עם הזהות המזויפת
        response = requests.get(csv_url, headers=headers)
        response.raise_for_status()
        
        # קריאת התוכן כקובץ CSV
        df = pd.read_csv(io.StringIO(response.text))
        
        # איתור עמודות (גמיש לשמות בעברית ובאנגלית)
        def find_col(keywords):
            for col in df.columns:
                if any(k.upper() in str(col).upper() for k in keywords):
                    return col
            return None

        col_name = find_col(['NAME', 'שם', 'כינוי'])
        col_yield = find_col(['YIELD_DAILY', 'תשואה', 'יומית'])
        col_fee = find_col(['FEE', 'ניהול', 'שכ"נ'])

        if not col_name or not col_yield or not col_fee:
            print("Could not find columns. Columns present:", df.columns.tolist())
            return None

        # סינון קרנות כספיות כשרות
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר', na=False))
        ].copy()

        if kosher_df.empty:
            print("No funds matched the filter.")
            return None

        # המרה למספרים וחישוב נטו
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
        print(f"Error: {e}")
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
