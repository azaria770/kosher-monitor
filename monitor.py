import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # ה-API הפנימי של אתר MAYA (הבורסה) שמזין את הקישור ששלחת
    url = "https://api.tase.co.il/api/fund/mutual-funds"
    
    # פרמטרים התואמים בדיוק לסינון בקישור: כשרה, שקלית, ללא מניות (מסווג 26)
    payload = {
        "classificationType": 1,
        "classificationMajor": 7,
        "classificationMain": 26, # כספית שקלית
        "isKosherFund": True,
        "paymentPolicyId": 1,
        "taxStatus": 1,
        "sortColumn": "dayYield", # מיון לפי תשואה יומית
        "sortOrder": "descending", # סדר יורד
        "lang": "he"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://maya.tase.co.il/',
        'Content-Type': 'application/json'
    }
    
    try:
        print("🔗 שולף נתונים מסוננים ישירות ממערכת הדירוג של הבורסה...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # המבנה באתר מאיה הוא רשימה של אובייקטים תחת 'items' או ישירות
        data = response.json()
        funds = data.get('items', data) if isinstance(data, dict) else data
        
        if not funds:
            print("⚠️ לא נמצאו קרנות העונות לסינון בבורסה.")
            return None
            
        df = pd.DataFrame(funds)
        
        # שמות העמודות ב-API של MAYA
        col_name = 'fundName'
        col_yield = 'dayYield'       # תשואה יומית (באחוזים)
        col_fee = 'managementFee'    # דמי ניהול שנתיים (באחוזים)
        
        # מאחר והנתונים כבר מגיעים ממוינים מהבורסה (sortOrder=descending)
        # הקרן הראשונה היא המנצחת לפי תשואה יומית
        winner = df.iloc[0]
        
        # חישוב תשואה נטו יומית (ברוטו פחות דמי ניהול/365)
        # שים לב: בקרנות כספיות דמי הניהול כבר נמוכים והתשואה משקפת את ריבית בנק ישראל
        net_yield = float(winner[col_yield]) - (float(winner[col_fee]) / 365)
        
        return {
            'NAME': winner[col_name],
            'NET': net_yield,
            'FEE': winner[col_fee],
            'GROSS': winner[col_yield]
        }

    except Exception as e:
        print(f"❌ שגיאה בשליפת הנתונים מהבורסה: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת (לפי אתר מאיה):*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 תשואה נטו יומית: `{winner['NET']:.4f}%` \n"
            f"📈 תשואה ברוטו: `{winner['GROSS']}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%` \n\n"
            f"ℹ️ הנתונים מסוננים לכספית שקלית כשרה בלבד."
        )
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("🚀 ההודעה נשלחה בהצלחה בהתאם לסינון המבוקש!")
