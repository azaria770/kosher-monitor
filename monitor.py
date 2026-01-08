import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # הכתובת הקבועה של ה-API המייצר את הנתונים בבורסה
    url = "https://api.tase.co.il/api/fund/mutual-funds"
    
    # פרמטרים המגדירים בדיוק את מה שביקשת: כספית שקלית (26) וכשרה
    payload = {
        "classificationType": 1,
        "classificationMajor": 7,
        "classificationMain": 26, 
        "isKosherFund": True,
        "paymentPolicyId": 1,
        "taxStatus": 1,
        "sortColumn": "dayYield",
        "sortOrder": "descending",
        "lang": "he"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://maya.tase.co.il/',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    
    try:
        print("📥 שולף נתונים ישירות מהבורסה (מקור MAYA)...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        funds = data.get('items', [])
        
        if not funds:
            print("⚠️ לא נמצאו נתונים בסינון המבוקש.")
            return None
            
        # הפיכת הנתונים לטבלה
        df = pd.DataFrame(funds)
        
        # הקרן הראשונה היא המנצחת לפי המיון שביקשנו (dayYield יורד)
        winner = df.iloc[0]
        
        # חילוץ נתונים
        fund_name = winner['fundName']
        gross_yield = float(winner['dayYield'])
        fee = float(winner['managementFee'])
        
        # חישוב נטו: תשואה יומית פחות חלק יחסי של דמי ניהול
        net_yield = gross_yield - (fee / 365)
        
        return {
            'NAME': fund_name,
            'NET': net_yield,
            'FEE': fee,
            'GROSS': gross_yield
        }

    except Exception as e:
        print(f"❌ שגיאה בשליפת הנתונים: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת (MAYA):*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 תשואה נטו יומית: `{winner['NET']:.4f}%` \n"
            f"📈 תשואה ברוטו: `{winner['GROSS']}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%` \n\n"
            f"✅ הנתונים נשלפו ומוינו אוטומטית ממערכת הבורסה."
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("🚀 ההודעה נשלחה בהצלחה לטלגרם!")
