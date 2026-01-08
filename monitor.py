import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # כתובת הורדה ישירה
    csv_url = "https://data.gov.il/dataset/e6fce050-705d-4f05-9502-0e23805494d9/resource/633db711-a3f3-469c-a6fd-059e09d82998/download/funds.csv"
    
    try:
        # הורדת הנתונים
        df = pd.read_csv(csv_url)
        
        # איתור אוטומטי של עמודות לפי מילות מפתח (כדי למנוע שגיאות שמות)
        col_name = [c for c in df.columns if 'NAME' in c.upper() or 'שם' in c][0]
        col_yield = [c for c in df.columns if 'YIELD_DAILY' in c.upper() or 'תשואה' in c][0]
        col_fee = [c for c in df.columns if 'FEE' in c.upper() or 'ניהול' in c][0]
        
        # 1. סינון: רק כספיות ורק כשרות
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשרה|כשר', na=False))
        ].copy()

        # 2. המרה למספרים וניקוי
        kosher_df[col_yield] = pd.to_numeric(kosher_df[col_yield], errors='coerce').fillna(0)
        kosher_df[col_fee] = pd.to_numeric(kosher_df[col_fee], errors='coerce').fillna(0)

        # 3. חישוב נטו יומית
        kosher_df['NET_PROFIT'] = kosher_df[col_yield] - (kosher_df[col_fee] / 365)

        # 4. מציאת המנצחת
        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        return {
            'NAME': winner[col_name],
            'NET_PROFIT': winner['NET_PROFIT'],
            'MANAGEMENT_FEE': winner[col_fee]
        }
    except Exception as e:
        print(f"Error during calculation: {e}")
        return None

def send_to_telegram(winner):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    
    if winner:
        msg = (
            f"🏆 *הקרן הכספית הכשרה המנצחת להיום:*\n\n"
            f"📌 שם: *{winner['NAME']}*\n"
            f"💰 רווח נטו יומי משוער: `{winner['NET_PROFIT']:.4f}%` \n"
            f"📉 דמי ניהול שנתיים: `{winner['MANAGEMENT_FEE']}%` \n"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    winner_data = get_top_kosher_fund()
    if winner_data:
        send_to_telegram(winner_data)
    else:
        print("No fund found or error occurred.")
