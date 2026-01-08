import os
import requests
import pandas as pd
import json

def get_top_kosher_fund():
    # כתובת ה-API הרשמית של הבורסה לניירות ערך (TASE)
    # זהו המקור האמין ביותר בישראל, והוא מחזיר JSON נקי
    url = "https://api.tase.co.il/api/fund/fundlobby"
    
    # פרמטרים שנדרשים כדי שהבורסה תחשוב שאנחנו גולשים באתר שלה
    payload = {
        "lang": "1",         # עברית
        "type": "0",         # כל סוגי הקרנות
        "status": "0"        # קרנות פעילות
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://maya.tase.co.il/',
        'Content-Type': 'application/json',
        'Origin': 'https://maya.tase.co.il'
    }
    
    try:
        print("מתחבר ישירות לשרתי הבורסה לניירות ערך (TASE)...")
        # פנייה בשיטת POST (כמו שהאתר האמיתי עושה)
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # המרת התשובה ל-JSON
        data = response.json()
        
        # הנתונים נמצאים בדרך כלל תחת מפתח 'FundList' או ישר ברשימה
        funds_list = data.get('FundList', data) if isinstance(data, dict) else data
        
        if not funds_list:
            print("התקבל JSON ריק מהבורסה.")
            return None
            
        print(f"התקבלו נתונים עבור {len(funds_list)} קרנות.")
        
        df = pd.DataFrame(funds_list)
        
        # --- מיפוי עמודות חכם לפי המפתחות של הבורסה ---
        # שמות השדות ב-API של הבורסה הם באנגלית (למשל: fundName, currentYield)
        
        # 1. זיהוי עמודת שם
        col_name = next((c for c in df.columns if c in ['fundName', 'name', 'hebrewName']), None)
        # 2. זיהוי עמודת תשואה יומית (בבורסה זה לרוב changeRate או yield)
        col_yield = next((c for c in df.columns if c in ['changeRate', 'dailyChange', 'yield']), None)
        # 3. זיהוי דמי ניהול
        col_fee = next((c for c in df.columns if c in ['managementFee', 'yearlyFee']), None)
        # 4. זיהוי סיווג (כדי למצוא כספיות)
        col_class = next((c for c in df.columns if c in ['classificationName', 'subClassificationName']), None)

        # אם השמות השתנו, ננסה לחפש לפי טקסט
        if not col_name:
            col_name = next((c for c in df.columns if 'name' in c.lower()), None)
        if not col_yield:
            col_yield = next((c for c in df.columns if 'change' in c.lower() or 'yield' in c.lower()), None)
        if not col_fee:
            col_fee = next((c for c in df.columns if 'fee' in c.lower()), None)

        print(f"עמודות שזוהו: שם={col_name}, תשואה={col_yield}, דמי ניהול={col_fee}")

        # סינון: קרנות כספיות כשרות
        df[col_name] = df[col_name].astype(str)
        
        # חיפוש "כספית" בשם הקרן או בסיווג שלה
        is_money_fund = df[col_name].str.contains('כספית', na=False)
        if col_class:
             is_money_fund |= df[col_class].astype(str).str.contains('כספית', na=False)
             
        # חיפוש כשרות
        is_kosher = df[col_name].str.contains('כשר|מהדרין', na=False)
        
        kosher_df = df[is_money_fund & is_kosher].copy()

        print(f"נמצאו {len(kosher_df)} קרנות כספיות כשרות.")

        if kosher_df.empty:
            return None

        # המרה למספרים
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        
        # חישוב נטו: תשואה יומית פחות (דמי ניהול שנתיים חלקי 365)
        # שים לב: בבורסה התשואה היא באחוזים (למשל 0.01), ודמי הניהול גם (למשל 0.15)
        kosher_df['NET'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner[col_fee]
        }

    except Exception as e:
        print(f"שגיאה בתקשורת מול הבורסה: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום (מקור: הבורסה):*\n\n"
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
