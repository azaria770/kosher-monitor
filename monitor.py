import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # כתובת הורדה ישירה של הקובץ הגולמי - המקור הכי פחות ניתן לחסימה
    url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9?bom=true"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("מבצע הורדה ישירה של המאגר...")
        # הורדת הקובץ
        response = requests.get(url, headers=headers, timeout=45)
        response.raise_for_status()
        
        # קריאת הנתונים תוך התעלמות משורות פגומות
        df = pd.read_csv(io.StringIO(response.text), on_bad_lines='skip')
        
        # ניקוי שמות עמודות
        df.columns = df.columns.str.strip()
        
        # איתור עמודות קריטיות (עברית/אנגלית)
        col_name = next((c for c in df.columns if any(k in c.upper() for k in ['NAME', 'שם', 'כינוי'])), None)
        col_yield = next((c for c in df.columns if any(k in c.upper() for k in ['YIELD_DAILY', 'תשואה'])), None)
        col_fee = next((c for c in df.columns if any(k in c.upper() for k in ['MANAGEMENT_FEE', 'ניהול', 'שכ"נ'])), None)

        if not all([col_name, col_yield, col_fee]):
            print(f"שגיאה: לא נמצאו כל העמודות הדרושות. נמצאו: {df.columns.tolist()}")
            return None

        # המרה לטקסט וסינון קרנות כשרות
        df[col_name] = df[col_name].astype(str)
        # סינון: חייב להכיל 'כספ' וגם 'כשר' או 'מהדרין'
        kosher_df = df[
            (df[col_name].str.contains('כספ', na=False)) & 
            (df[col_name].str.contains('כשר|מהדרין', na=False))
        ].copy()

        if kosher_df.empty:
            print("לא נמצאו קרנות כשרות ברשימה שהורדה.")
            return None

        # ניקוי ערכים מספריים
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        
        # חישוב תשואה נטו
        kosher_df['NET_PROFIT'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        # מציאת המנצחת
        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET_PROFIT'],
            'FEE': winner[col_fee]
        }

    except Exception as e:
        print(f"שגיאת שליפה סופית: {e}")
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
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
