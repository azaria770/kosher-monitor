import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # כתובת גישה ישירה לנתוני קרנות נאמנות - המאגר הכי יציב
    url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9?bom=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("ניגש ישירות למאגר הנתונים...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # קריאת הנתונים תוך טיפול בעברית
        df = pd.read_csv(io.StringIO(response.text))
        
        # איתור עמודות (גמיש לשמות שונים)
        col_name = next((c for c in df.columns if 'NAME' in str(c).upper() or 'שם' in str(c)), df.columns[1])
        col_yield = next((c for c in df.columns if 'YIELD' in str(c).upper() or 'תשואה' in str(c)), None)
        col_fee = next((c for c in df.columns if 'FEE' in str(c).upper() or 'ניהול' in str(c)), None)

        # סינון: קרנות כספיות כשרות
        df[col_name] = df[col_name].astype(str)
        mask = (df[col_name].str.contains('כספית', na=False)) & (df[col_name].str.contains('כשר', na=False))
        kosher_df = df[mask].copy()

        if kosher_df.empty:
            print("לא נמצאו קרנות העונות לסינון.")
            return None

        # המרה למספרים וחישוב
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
        print(f"שגיאה בשליפת נתונים: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי משוער: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
