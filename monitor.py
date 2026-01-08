import os
import requests
import pandas as pd

def get_top_kosher_fund():
    csv_url = "https://data.gov.il/dataset/e6fce050-705d-4f05-9502-0e23805494d9/resource/633db711-a3f3-469c-a6fd-059e09d82998/download/funds.csv"
    
    try:
        # הורדת הנתונים עם הגדרת קידוד נפוצה לישראל
        df = pd.read_csv(csv_url, encoding='utf-8')
        
        # איתור עמודות בצורה חכמה (לפי מילות מפתח)
        def find_col(keywords):
            for col in df.columns:
                if any(k.upper() in col.upper() for k in keywords):
                    return col
            return None

        col_name = find_col(['NAME', 'שם', 'כינוי'])
        col_yield = find_col(['YIELD_DAILY', 'תשואה', 'יומית'])
        col_fee = find_col(['FEE', 'ניהול', 'שכ"נ'])

        # בדיקה אם נמצאו העמודות
        if not all([col_name, col_yield, col_fee]):
            print(f"Columns found: Name={col_name}, Yield={col_yield}, Fee={col_fee}")
            return None

        # סינון חכם: לא משנה אם זה "כספית" או "כספית-", הקוד ימצא
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False, case=False)) & 
            (df[col_name].str.contains('כשר', na=False, case=False))
        ].copy()

        print(f"Found {len(kosher_df)} kosher money funds.")

        if kosher_df.empty:
            print("No funds matched the filter.")
            return None

        # המרה למספרים
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)

        # חישוב נטו
        kosher_df['NET_PROFIT'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        # מציאת המנצחת
        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET_PROFIT': winner['NET_PROFIT'],
            'MANAGEMENT_FEE': winner[col_fee]
        }
    except Exception as e:
        print(f"Final error check: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    if winner:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי: `{winner['NET_PROFIT']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['MANAGEMENT_FEE']}%` \n"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    winner_data = get_top_kosher_fund()
    if winner_data:
        send_to_telegram(winner_data)
