import os
import time
import pandas as pd
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def get_top_kosher_fund():
    # כתובת ראשית - לכניסה וקבלת אישור
    main_page = "https://data.gov.il/dataset/fund-data"
    # הכתובת הישירה לקובץ
    csv_url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9?bom=true"

    print("🚀 מפעיל תותחים כבדים: Selenium Full-Browser Mode...")

    options = Options()
    options.add_argument("--headless=new")  # מצב headless מודרני
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. כניסה לדף הראשי כדי לעורר את ה-WAF (חומת האש)
        print("1. נכנס לאתר הראשי וממתין לפענוח האתגר...")
        driver.get(main_page)
        
        # המתנה נדיבה מאוד - תן לחסימה לסיים את כל הבדיקות שלה
        time.sleep(25)
        
        # בדיקה אם עדיין רואים את מסך החסימה (לוגיקה בסיסית)
        if "f1xx" in driver.page_source:
            print("⚠️ אזהרה: נראה שהחסימה עדיין לא עברה לגמרי. מנסה בכל זאת...")

        # 2. הורדת הקובץ *מתוך* הדפדפן עצמו (בלי requests חיצוני)
        print("2. מבצע הורדה באמצעות מנוע ה-JS של הדפדפן...")
        # הטריק: שימוש ב-fetch בתוך הקונסולה של הדפדפן כדי לשמור על ה-Session
        csv_content = driver.execute_script(f"""
            return fetch('{csv_url}').then(response => {{
                if (!response.ok) {{
                    throw new Error('Network response was not ok');
                }}
                return response.text();
            }});
        """)
        
        if not csv_content or "<html" in csv_content[:100]:
            print("❌ שגיאה: התקבל תוכן HTML במקום CSV (החסימה לא נפרצה).")
            print(f"תחילת התוכן: {csv_content[:200]}")
            return None

        print(f"✅ הקובץ ירד בהצלחה! גודל: {len(csv_content)} תווים.")
        
        # 3. עיבוד הנתונים
        df = pd.read_csv(StringIO(csv_content))
        df.columns = df.columns.str.strip()
        
        col_name = next((c for c in df.columns if any(k in c for k in ['שם', 'NAME', 'קרן'])), None)
        col_yield = next((c for c in df.columns if any(k in c for k in ['תשואה', 'YIELD', 'יומית'])), None)
        col_fee = next((c for c in df.columns if any(k in c for k in ['ניהול', 'FEE', 'שכ"נ'])), None)

        if not col_name:
            print(f"לא נמצאו עמודות. רשימה: {list(df.columns)}")
            return None

        df[col_name] = df[col_name].astype(str)
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר|מהדרין', na=False))
        ].copy()

        print(f"נמצאו {len(kosher_df)} קרנות כשרות.")

        if kosher_df.empty:
            return None

        # המרה וחישוב
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
        print(f"💥 שגיאה קריטית בדפדפן: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def send_to_telegram(winner):
    # כאן אנחנו משתמשים בספרייה סטנדרטית כי לטלגרם אין חסימות כאלו
    import requests 
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                          json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"שגיאה בשליחה: {e}")

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
