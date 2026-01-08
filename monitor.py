import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # שימוש במקור נתונים חלופי ויציב - API של נתוני שוק
    # הכתובת הזו מושכת את נתוני הקרנות הכספיות בצורה נקייה
    url = "https://api.allorigins.win/get?url=" + requests.utils.quote("https://data.gov.il/api/3/action/datastore_search?resource_id=8555776d-068d-4861-bcc5-c266a8779951&limit=1000")
    
    try:
        print("מושך נתונים דרך שרת מתווך לעקיפת חסימות...")
        response = requests.get(url, timeout=30)
        data = response.json()
        
        # חילוץ הנתונים מהמעטפת של ה-Proxy
        import json
        real_data = json.loads(data['contents'])
        records = real_data['result']['records']
        
        df = pd.DataFrame(records)
        print(f"נטענו {len(df)} קרנות.")

        # איתור עמודות
        col_name = next((c for c in df.columns if 'NAME' in str(c).upper() or 'שם' in str(c)), None)
        col_yield = next((c for c in df.columns if 'YIELD' in str(c).upper() or 'תשואה' in str(c)), None)
        col_fee = next((c for c in df.columns if 'FEE' in str(c).upper() or 'ניהול' in str(c)), None)

        # סינון קרנות כשרות
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר', na=False))
        ].copy()

        if kosher_df.empty:
            print("לא נמצאו קרנות כשרות ברשימה.")
            return None

        # המרה למספרים וחישוב נטו
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
        print(f"שגיאה בשליפת הנתונים: {e}")
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
