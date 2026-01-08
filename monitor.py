import os
import requests
import pandas as pd
from io import StringIO

def get_top_kosher_fund():
    # מקור מידע חלופי ויציב - דף הקרנות הכספיות
    url = "https://www.bizportal.co.il/money-market-funds"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("מתחבר למקור נתונים כלכלי חלופי...")
        response = requests.get(url, headers=headers, timeout=30)
        
        # קריאת הטבלאות מהדף
        tables = pd.read_html(StringIO(response.text))
        
        # מציאת הטבלה עם הכי הרבה שורות (זו טבלת הנתונים)
        df = max(tables, key=len)
        
        # ניקוי שמות עמודות
        df.columns = [str(c).strip() for c in df.columns]
        
        # איתור עמודות קריטיות
        col_name = next((c for c in df.columns if 'שם' in c), df.columns[0])
        col_yield = next((c for c in df.columns if 'תשואה' in c and 'שנה' not in c), None)
        col_fee = next((c for c in df.columns if 'ניהול' in c), None)

        # סינון קרנות כשרות
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[df[col_name].str.contains('כשרה|כשר|מהדרין', na=False)].copy()
        
        if kosher_df.empty:
            print("לא נמצאו קרנות כשרות בטבלה זו.")
            return None

        # ניקוי מספרים (אחוזים וסימנים)
        def clean_num(val):
            if pd.isna(val): return 0
            s = str(val).replace('%', '').replace('+', '').replace(' ', '').strip()
            try: return float(s)
            except: return 0

        # חישוב נטו (בהנחה שהתשואה היא שנתית מצטברת או יומית)
        kosher_df['yield_val'] = kosher_df[col_yield].apply(clean_num)
        kosher_df['fee_val'] = kosher_df[col_fee].apply(clean_num)
        
        # מיון לפי התשואה הכי גבוהה
        winner = kosher_df.sort_values(by='yield_val', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'YIELD': winner['yield_val'],
            'FEE': winner['fee_val']
        }

    except Exception as e:
        print(f"שגיאת חילוץ סופית: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"📈 תשואה: `{winner['YIELD']}%` \n"
            f"📉 דמי ניהול: `{winner['FEE']}%`"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
