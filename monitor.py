import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # כתובת ה-API של מאגר נתוני קרנות נאמנות
    url = "https://data.gov.il/api/3/action/datastore_search"
    resource_id = "633db711-a3f3-469c-a6fd-059e09d82998"
    
    params = {
        'resource_id': resource_id,
        'limit': 2000 # מושך את כל הקרנות הקיימות
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        records = data['result']['records']
        df = pd.DataFrame(records)

        # 1. סינון: רק כספיות ורק כשרות
        # במאגר הממשלתי 'NAME' הוא שם הקרן
        kosher_df = df[
            (df['NAME'].str.contains('כספית', na=False)) & 
            (df['NAME'].str.contains('כשרה|כשר', na=False))
        ].copy()

        # 2. ניקוי נתונים - המרה למספרים
        # 'YIELD_DAILY' - תשואה יומית, 'MANAGEMENT_FEE' - דמי ניהול שנתיים
        kosher_df['YIELD_DAILY'] = pd.to_numeric(kosher_df['YIELD_DAILY'], errors='coerce').fillna(0)
        kosher_df['MANAGEMENT_FEE'] = pd.to_numeric(kosher_df['MANAGEMENT_FEE'], errors='coerce').fillna(0)

        # 3. חישוב נטו יומית (תשואה יומית פחות דמי ניהול יחסיים ליום)
        kosher_df['NET_PROFIT'] = kosher_df['YIELD_DAILY'] - (kosher_df['MANAGEMENT_FEE'] / 365)

        # 4. מציאת הקרן המובילה
        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        return winner
    except Exception as e:
        print(f"Error: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    if not winner.empty:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET_PROFIT']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['MANAGEMENT_FEE']}%` \n"
            f"📅 עדכון אחרון: {winner['DATE']}"
        )
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

if __name__ == "__main__":
    top_fund = get_top_kosher_fund()
    if top_fund is not None:
        send_to_telegram(top_fund)
