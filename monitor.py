import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # זהו ה-Resource ID המדויק והפעיל נכון לעכשיו באתר data.gov.il
    resource_id = "8555776d-068d-4861-bcc5-c266a8779951"
    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}&limit=5000"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        print("Connecting directly to the latest data resource...")
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if not data.get('success'):
            print(f"API Access Failed: {data.get('error')}")
            return None
            
        records = data['result']['records']
        df = pd.DataFrame(records)
        print(f"Successfully retrieved {len(df)} records.")

        # איתור עמודות גמיש
        col_name = next((c for c in df.columns if 'NAME' in str(c).upper() or 'שם' in str(c)), None)
        col_yield = next((c for c in df.columns if 'YIELD' in str(c).upper() or 'תשואה' in str(c)), None)
        col_fee = next((c for c in df.columns if 'FEE' in str(c).upper() or 'ניהול' in str(c)), None)

        # המרת שמות הקרנות לטקסט וסינון "כספית" + "כשר"
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר', na=False))
        ].copy()
        
        print(f"Filtered down to {len(kosher_df)} kosher money funds.")

        if kosher_df.empty:
            return None

        # המרה למספרים וחישוב נטו
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)
        
        # חישוב: (תשואה יומית) פחות (דמי ניהול שנתיים / 365)
        kosher_df['NET'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        winner = kosher_df.sort_values(by='NET', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET': winner['NET'],
            'FEE': winner[col_fee],
            'DAILY': winner[col_yield]
        }

    except Exception as e:
        print(f"Critical Error: {e}")
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
        print("Success! Notification sent to Telegram.")
