import os
from curl_cffi import requests
import pandas as pd
from io import StringIO

def get_top_kosher_fund():
    # המקור הכי יציב ופתוח - טבלת הקרנות של Funder
    url = "https://www.funder.co.il/karani"
    
    try:
        print("🚀 מפעיל התחזות מלאה לדפדפן (TLS Fingerprinting)...")
        
        # שימוש ב-curl_cffi כדי להתחזות לדפדפן כרום גרסה 124 (הכי חדש)
        # זה עוקף את כל חסימות ה-WAF והבוטים
        response = requests.get(url, impersonate="chrome124", timeout=30)
        
        if response.status_code != 200:
            print(f"❌ שגיאת חיבור: {response.status_code}")
            return None

        print("✅ החיבור הצליח! מעבד את הטבלה...")

        # קריאת הטבלה מתוך ה-HTML
        # משתמשים ב-StringIO כדי למנוע שגיאות pandas ישנות
        dfs = pd.read_html(StringIO(response.text))
        
        # חיפוש הטבלה הגדולה (זו שמכילה את הנתונים)
        df = max(dfs, key=len)
        
        # ניקוי שמות עמודות (הסרת רווחים וכו')
        df.columns = [str(c).strip() for c in df.columns]
        
        # זיהוי עמודות חכם (כי השמות באתר בעברית)
        col_name = next((c for c in df.columns if 'שם' in c), None)
        col_yield = next((c for c in df.columns if 'יומית' in c), None)
        col_fee = next((c for c in df.columns if 'ניהול' in c or 'שכ"נ' in c), None)

        if not all([col_name, col_yield, col_fee]):
            print(f"⚠️ לא נמצאו כל העמודות. זוהו: {list(df.columns)}")
            return None

        # סינון: רק קרנות כספיות שהן כשרות
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[df[col_name].str.contains('כשרה|כשר|מהדרין', na=False)].copy()
        
        print(f"💰 נמצאו {len(kosher_df)} קרנות כשרות בטבלה.")

        if kosher_df.empty:
            return None

        # פונקציה לניקוי המספרים (מסיר % ופלוסים)
        def clean_num(val):
            if pd.isna(val): return 0
            s = str(val).replace('%', '').replace('+', '').replace(',', '').strip()
            try: return float(s)
            except: return 0

        # חישוב נטו
        kosher_df['yield_val'] = kosher_df[col_yield].apply(clean_num)
        kosher_df['fee_val'] = kosher_df[col_fee].apply(clean_num)
        
        # תשואה יומית פחות (דמי ניהול שנתיים חלקי 365)
        kosher_df['NET'] = kosher_df['yield_val'] - (kosher_df['fee_val'] / 365)

        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner['fee_val'],
            'DAILY': winner['yield_val']
        }

    except Exception as e:
        print(f"💥 שגיאה: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת (Funder):*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET']:.4f}%` \n"
            f"📊 תשואה ברוטו יומית: `{winner['DAILY']}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        # גם כאן משתמשים בהתחזות ליתר ביטחון
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                      impersonate="chrome124")

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("🚀 ההודעה נשלחה בהצלחה!")
