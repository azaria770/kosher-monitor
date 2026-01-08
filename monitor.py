import os
import time
import pandas as pd
import requests
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_top_kosher_fund():
    # כתובת הדף הראשי של המאגר (לא הקובץ הישיר, כדי לעבור את החסימה בדף)
    main_page_url = "https://data.gov.il/dataset/fund-data"
    # הכתובת הישירה לקובץ (נשתמש בה אחרי שנשיג אישור מהחסימה)
    csv_url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9?bom=true"
    
    print("מפעיל דפדפן כרום וירטואלי (Selenium) לעקיפת החסימה...")
    
    # הגדרות לדפדפן כדי שירוץ על השרת של GitHub
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # רוץ ללא מסך
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # התחזות למשתמש רגיל
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        # הפעלת הדפדפן
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 1. כניסה לדף הראשי כדי "לקבל אישור" (Cookies) מההגנה של הממשלה
        print("נכנס לאתר הממשלתי וממתין לפענוח החסימה...")
        driver.get(main_page_url)
        
        # המתנה קריטית! נותנים ל-JavaScript של החסימה לרוץ
        time.sleep(15) 
        
        print("החסימה אמורה לעבור כעת. שואב את העוגיות (Cookies)...")
        # העתקת העוגיות מהדפדפן
        selenium_cookies = driver.get_cookies()
        session_cookies = {c['name']: c['value'] for c in selenium_cookies}
        session_headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent;")
        }
        driver.quit() # סגירת הדפדפן

        # 2. שימוש בעוגיות כדי להוריד את הקובץ ישירות
        print("מוריד את הקובץ באמצעות האישור שהושג...")
        response = requests.get(csv_url, headers=session_headers, cookies=session_cookies, timeout=60)
        
        if "<html" in response.text[:100]:
            print("שגיאה: עדיין חסום. נסה להגדיל את זמן ההמתנה.")
            return None

        # 3. פענוח ועיבוד הנתונים (כמו בגרסה 18 שעבדה לוגית)
        content = response.content
        try:
            decoded_content = content.decode('utf-8-sig')
        except:
            try:
                decoded_content = content.decode('cp1255')
            except:
                decoded_content = content.decode('iso-8859-8', errors='replace')

        df = pd.read_csv(StringIO(decoded_content), on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        
        # זיהוי עמודות
        col_name = next((c for c in df.columns if any(k in c for k in ['שם', 'NAME', 'קרן'])), None)
        col_yield = next((c for c in df.columns if any(k in c for k in ['תשואה', 'YIELD', 'יומית'])), None)
        col_fee = next((c for c in df.columns if any(k in c for k in ['ניהול', 'FEE', 'שכ"נ'])), None)

        if not col_name:
            print(f"לא נמצאו עמודות. רשימה: {list(df.columns)}")
            return None

        # סינון
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר|מהדרין', na=False))
        ].copy()

        print(f"הצלחה! נמצאו {len(kosher_df)} קרנות כשרות.")

        if kosher_df.empty:
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
        print(f"שגיאה בתהליך הדפדפן: {e}")
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
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                          json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            print(f"שגיאה בשליחה לטלגרם: {e}")

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
