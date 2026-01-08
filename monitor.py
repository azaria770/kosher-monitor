import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # המזהה הקבוע של חבילת הנתונים (Dataset)
    package_id = "fund-data"
    package_url = f"https://data.gov.il/api/3/action/package_show?id={package_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("Finding the latest resource ID...")
        package_response = requests.get(package_url, headers=headers, timeout=30)
        package_data = package_response.json()
        
        # חיפוש המשאב של "מחירי קרנות" בתוך החבילה
        resources = package_data['result']['resources']
        # אנחנו מחפשים את המשאב שהשם שלו מכיל "מחירים" או "מחירי"
        resource = next((r for r in resources if "מחירים" in r['name']), resources[0])
        resource_id = resource['id']
        print(f"Using latest Resource ID: {resource_id}")

        # עכשיו שולפים את הנתונים עם ה-ID שמצאנו הרגע
        data_url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}&limit=5000"
        data_response = requests.get(data_url, headers=headers, timeout=30)
        data = data_response.json()
        
        records = data['result']['records']
        df = pd.DataFrame(records)
        print(f"Loaded {len(df)} records.")

        # איתור עמודות (גמיש לשמות שונים)
        col_name = next((c for c in df.columns if 'NAME' in str(c).upper() or 'שם' in str(c)), None)
        col_yield = next((c for c in df.columns if 'YIELD' in str(c).upper() or 'תשואה' in str(c)), None)
        col_fee = next((c for c in df.columns if 'FEE' in str(c).upper() or 'ניהול' in str(c)), None)

        # המרה לטקסט וסינון
        df[col_name] = df[col_name].astype(str)
        mask = (df[col_name].str.contains('כספית', na=False)) & \
               (df[col_name].str.contains('כשר', na=False))
        
        kosher_df = df[mask].copy()
        
        if kosher_df.empty:
            print("No funds found with current filters.")
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
        print(f"Process Error: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner and token and chat_id:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['FEE']}%` \n"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    top_fund = get_top_kosher_fund()
    if top_fund:
        send_to_telegram(top_fund)
        print("Success! Notification sent.")
