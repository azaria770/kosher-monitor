import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # זהו ה-ID המדויק שפעיל כרגע במערכת יעל/ממשל זמין
    resource_id = "e6fce050-705d-4f05-9502-0e23805494d9" 
    # אם ה-API של החיפוש נחסם, אנחנו ניגשים ישירות להורדת הנתונים
    csv_url = f"https://data.gov.il/datastore/dump/{resource_id}?bom=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # הורדת ה-CSV ישירות (עוקף את שגיאות ה-API 'Resource not found')
        response = requests.get(csv_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # קריאת הנתונים
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        # איתור עמודות גמיש
        def find_col(keys):
            for c in df.columns:
                if any(k in str(c).upper() for k in keys): return c
            return None

        col_name = find_col(['FUND_NAME', 'NAME', 'שם'])
        col_yield = find_col(['YIELD_DAILY', 'תשואה', 'יומית'])
        col_fee = find_col(['MANAGEMENT_FEE', 'FEE', 'ניהול', 'שכ"נ'])

        # סינון קרנות כספיות כשרות
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר', na=False))
        ].copy()

        if kosher_df.empty:
            print("No matching funds found.")
            return None

        # חישוב נטו
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        kosher_df['NET'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner[col_fee]
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
            f"💰 רווח נטו יומי: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    winner_data = get_top_kosher_fund()
    if winner_data:
        send_to_telegram(winner_data)
        print("Done! Check Telegram.")
