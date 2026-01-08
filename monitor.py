import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # כתובת ה-API הרשמית של הבורסה לניירות ערך
    url = "https://api.tase.co.il/api/fund/fundlobby"
    
    payload = {"lang": "1", "type": "0", "status": "0"}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://maya.tase.co.il/',
        'Content-Type': 'application/json'
    }
    
    try:
        print("🔗 מתחבר ישירות לשרתי הבורסה (TASE)...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        funds = data.get('FundList', [])
        if not funds:
            print("⚠️ לא התקבלו נתונים מהבורסה.")
            return None
            
        df = pd.DataFrame(funds)
        
        # זיהוי עמודות לפי מבנה הבורסה
        col_name = 'fundName'
        col_yield = 'dailyChange' # תשואה יומית
        col_fee = 'managementFee' # דמי ניהול שנתיים
        col_class = 'subClassificationName'

        # סינון: קרנות כספיות כשרות
        df[col_name] = df[col_name].astype(str)
        mask = (df[col_name].str.contains('כספית', na=False) | df[col_class].astype(str).str.contains('כספית', na=False)) & \
               (df[col_name].str.contains('כשר|מהדרין', na=False))
        
        kosher_df = df[mask].copy()
        print(f"📊 נמצאו {len(kosher_df)} קרנות כספיות כשרות.")

        if kosher_df.empty:
            return None

        # המרה וחישוב נטו
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        
        # נטו = תשואה יומית פחות (דמי ניהול שנתיים / 365)
        kosher_df['NET'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner[col_fee]
        }

    except Exception as e:
        print(f"❌ שגיאה בשליפה מהבורסה: {e}")
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
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("🚀 ההודעה נשלחה בהצלחה!")
