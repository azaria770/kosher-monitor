import os
import requests
import pandas as pd
from io import StringIO

def get_top_kosher_fund():
    # דף הקרנות הכספיות ב-Funder - מעודכן ויציב בהרבה מה-API הממשלתי
    url = "https://www.funder.co.il/karani"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("Connecting to financial portal...")
        response = requests.get(url, headers=headers, timeout=30)
        
        # קריאת הטבלאות מהדף
        tables = pd.read_html(StringIO(response.text))
        # בדרך כלל הטבלה הראשונה או השנייה היא הטבלה עם הנתונים
        df = tables[0] if len(tables[0]) > 10 else tables[1]
        
        # ניקוי שמות עמודות
        df.columns = [str(c).strip() for c in df.columns]
        
        # איתור עמודות קריטיות
        col_name = next((c for c in df.columns if 'שם' in c), df.columns[0])
        col_yield = next((c for c in df.columns if 'יומית' in c), None)
        col_fee = next((c for c in df.columns if 'ניהול' in c or 'שכ"נ' in c), None)

        # סינון קרנות כשרות בלבד
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[df[col_name].str.contains('כשרה|כשר', na=False)].copy()
        
        if kosher_df.empty:
            print("No kosher funds found in the current table.")
            return None

        # פונקציה לניקוי מספרים מתווים כמו '%' או '+'
        def clean_num(val):
            if pd.isna(val): return 0
            s = str(val).replace('%', '').replace('+', '').strip()
            try: return float(s)
            except: return 0

        # חישוב התשואה נטו (יומית פחות חלק יחסי של דמי ניהול שנתיים)
        kosher_df['yield_num'] = kosher_df[col_yield].apply(clean_num)
        kosher_df['fee_num'] = kosher_df[col_fee].apply(clean_num)
        kosher_df['NET'] = kosher_df['yield_num'] - (kosher_df['fee_num'] / 365)

        # בחירת הקרן עם התשואה הגבוהה ביותר
        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner['fee_num'],
            'DAILY': winner['yield_num']
        }

    except Exception as e:
        print(f"Final Fallback Error: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי משוער: `{winner['NET']:.4f}%` \n"
            f"📊 תשואה ברוטו יומית: `{winner['DAILY']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%`"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("Success! Notification sent.")
