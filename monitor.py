import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # המזהה הקבוע של "חבילת" נתוני הקרנות (לא משתנה)
    package_id = "fund-data"
    search_url = f"https://data.gov.il/api/3/action/package_show?id={package_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # שלב 1: מציאת ה-ID המעודכן ביותר של קובץ המחירים
        print("Searching for the latest resource ID...")
        package_res = requests.get(search_url, headers=headers, timeout=30)
        package_data = package_res.json()
        
        # חיפוש המשאב ששמו מכיל "מחירים" (המקור לנתונים היומיים)
        resources = package_data['result']['resources']
        resource_id = next(r['id'] for r in resources if "מחירים" in r['name'])
        print(f"Found latest Resource ID: {resource_id}")

        # שלב 2: שליפת הנתונים עם ה-ID שמצאנו
        data_url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}&q=כספית&limit=1000"
        data_res = requests.get(data_url, headers=headers, timeout=30)
        data = data_res.json()
        
        records = data['result']['records']
        if not records:
            return None
            
        df = pd.DataFrame(records)
        
        # איתור עמודות (גמיש לשמות שונים)
        col_name = next((c for c in df.columns if 'NAME' in str(c).upper() or 'שם' in str(c)), None)
        col_yield = next((c for c in df.columns if 'YIELD' in str(c).upper() or 'תשואה' in str(c)), None)
        col_fee = next((c for c in df.columns if 'FEE' in str(c).upper() or 'ניהול' in str(c)), None)

        # סינון קרנות כשרות
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[df[col_name].str.contains('כשרה|כשר', na=False)].copy()
        
        if kosher_df.empty:
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
        print(f"Error: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי משוער: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%` \n"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("Success! Notification sent.")
