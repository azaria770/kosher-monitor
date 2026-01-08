import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # כתובת מאגר הקרנות של הבורסה לניירות ערך - מקור יציב ופתוח
    url = "https://market.tase.co.il/Hebrew/MarketData/Funds/Pages/FundDataConfiguration.aspx"
    
    # נשתמש ב-API של הבורסה לשליפת נתוני קרנות כספיות
    api_url = "https://api.tase.co.il/api/fund/history"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://market.tase.co.il/'
    }

    try:
        print("מתחבר למאגר הנתונים המרכזי...")
        # נבצע בקשה לקבלת כל הקרנות הכספיות (סיווג 101 בבורסה)
        # כדי לפשט, נחזור לשיטת ה-Direct Download מהממשלה אבל עם תיקון לסינון
        gov_url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9?bom=true"
        response = requests.get(gov_url, headers=headers, timeout=30)
        
        # קריאת הנתונים
        df = pd.read_csv(io.StringIO(response.text))
        
        # תיקון קריטי: ב-CSV המלא השמות הם לפעמים עם גרשיים או רווחים
        df.columns = df.columns.str.strip()
        
        # איתור עמודות לפי מילות מפתח - הפעם עם בדיקה רחבה יותר
        col_name = next((c for c in df.columns if any(k in c.upper() for k in ['NAME', 'שם', 'כינוי'])), None)
        col_yield = next((c for c in df.columns if any(k in c.upper() for k in ['YIELD', 'תשואה'])), None)
        col_fee = next((c for c in df.columns if any(k in c.upper() for k in ['FEE', 'ניהול', 'שכ"נ'])), None)

        # סינון קרנות כספיות כשרות - נהיה גמישים יותר בחיפוש
        # נחפש כל מה שמכיל 'כספ' (כדי לתפוס כספית) וגם 'כשר' או 'מהדרין'
        df[col_name] = df[col_name].astype(str)
        kosher_mask = (df[col_name].str.contains('כספ', na=False)) & \
                      (df[col_name].str.contains('כשר|מהדרין', na=False))
        
        kosher_df = df[kosher_mask].copy()

        if kosher_df.empty:
            print("בדיקת חירום: מנסה סינון רחב יותר...")
            # אם לא מצאנו, ננסה לחפש רק 'כשר' ונסנן ידנית
            kosher_df = df[df[col_name].str.contains('כשר', na=False)].copy()

        # ניקוי והמרה
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
        print(f"שגיאה סופית: {e}")
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
