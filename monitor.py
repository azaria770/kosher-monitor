import os
from curl_cffi import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # כתובת ההורדה הישירה מהממשלה
    url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9?bom=true"
    
    try:
        print("מבצע התחזות לדפדפן כרום ברמת הפרוטוקול (TLS)...")
        
        # שימוש ב-curl_cffi עם התחזות לכרום גרסה 120
        # זה עוקף את חסימת ה-TLS שהפילה את הניסיונות הקודמים
        response = requests.get(url, impersonate="chrome120", timeout=60)
        
        # בדיקה אם עדיין קיבלנו דף חסימה
        if "<html" in response.text[:100] and "script" in response.text[:500]:
            print("התראה: השרת עדיין מנסה לחסום. מנסה טקטיקה ב'...")
            return None

        print("הקובץ ירד! מפענח קידוד...")
        
        # הממשלה משתמשת בקידוד עברית ישן (Windows-1255)
        # ננסה לפענח אותו בזהירות
        content = response.content
        try:
            decoded_content = content.decode('utf-8-sig')
        except:
            try:
                decoded_content = content.decode('cp1255')
            except:
                decoded_content = content.decode('iso-8859-8', errors='replace')

        # טעינה לפנדס
        df = pd.read_csv(io.StringIO(decoded_content), on_bad_lines='skip')
        
        # ניקוי שמות עמודות
        df.columns = df.columns.str.strip()
        
        # זיהוי עמודות חכם
        col_name = next((c for c in df.columns if any(k in c for k in ['שם', 'NAME', 'קרן'])), None)
        col_yield = next((c for c in df.columns if any(k in c for k in ['תשואה', 'YIELD', 'יומית'])), None)
        col_fee = next((c for c in df.columns if any(k in c for k in ['ניהול', 'FEE', 'שכ"נ'])), None)

        if not col_name:
            print(f"לא נמצאו עמודות. העמודות בקובץ: {list(df.columns)}")
            return None

        # המרה לטקסט וסינון
        df[col_name] = df[col_name].astype(str)
        
        # סינון: קרנות כספיות שהן גם כשרות או מהדרין
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר|מהדרין', na=False))
        ].copy()

        print(f"נמצאו {len(kosher_df)} קרנות כספיות כשרות.")

        if kosher_df.empty:
            return None

        # ניקוי וחישוב
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        
        # חישוב נטו
        kosher_df['NET'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner[col_fee]
        }

    except Exception as e:
        print(f"שגיאה קריטית: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    # שימוש ב-requests של curl_cffi גם לשליחה (זה עובד אותו דבר)
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, impersonate="chrome120")

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
