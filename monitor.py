import os
import cloudscraper
import pandas as pd
import io

def get_top_kosher_fund():
    # כתובת ההורדה הישירה
    url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9"
    
    try:
        print("מפעיל עוקף-חסימות (CloudScraper)...")
        # יצירת סקרייפר שמחקה דפדפן כרום רגיל
        scraper = cloudscraper.create_scraper()
        
        # ביצוע הבקשה דרך הסקרייפר
        response = scraper.get(url)
        
        # בדיקה אם עדיין קיבלנו חסימה (אם התוכן מכיל HTML במקום CSV)
        if "<html>" in response.text[:100]:
            print("החסימה עדיין פעילה. השרת שלח דף HTML.")
            # הדפסת חלק מהתוכן לדיבוג
            print(f"תוכן שהתקבל: {response.text[:200]}")
            return None

        print("הקובץ ירד בהצלחה. מפענח...")
        
        # ניסיון פענוח עם קידודים שונים לעברית
        try:
            content = response.content.decode('utf-8-sig')
        except:
            content = response.content.decode('cp1255')
            
        df = pd.read_csv(io.StringIO(content))
        
        # ניקוי רווחים בשמות העמודות
        df.columns = df.columns.str.strip()
        
        # זיהוי עמודות חכם
        col_name = next((c for c in df.columns if any(k in c for k in ['שם', 'NAME', 'קרן'])), None)
        col_yield = next((c for c in df.columns if any(k in c for k in ['תשואה', 'YIELD', 'יומית'])), None)
        col_fee = next((c for c in df.columns if any(k in c for k in ['ניהול', 'FEE', 'שכ"נ'])), None)

        if not col_name:
            print(f"לא נמצאו עמודות מתאימות. עמודות קיימות: {list(df.columns)}")
            return None

        # המרה לטקסט וסינון
        df[col_name] = df[col_name].astype(str)
        
        # סינון: חייב להכיל 'כספית' וגם ('כשר' או 'מהדרין')
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר|מהדרין', na=False))
        ].copy()

        print(f"נמצאו {len(kosher_df)} קרנות כשרות.")

        if kosher_df.empty:
            return None

        # המרה למספרים
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
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        # שימוש ב-cloudscraper גם לשליחה לטלגרם ליתר ביטחון, למרות ששם requests עובד
        scraper = cloudscraper.create_scraper()
        scraper.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
