import os
import requests
import pandas as pd

def get_top_kosher_fund():
    # כתובת להורדה ישירה של הקובץ - הרבה יותר יציב מול השרת הממשלתי
    csv_url = "https://data.gov.il/dataset/e6fce050-705d-4f05-9502-0e23805494d9/resource/633db711-a3f3-469c-a6fd-059e09d82998/download/funds.csv"
    
    try:
        # הורדת הנתונים כקובץ CSV
        df = pd.read_csv(csv_url)

        # 1. סינון: רק כספיות ורק כשרות
        # ב-CSV הממשלתי השמות הם בעברית לפעמים, אז נחפש בשם הקרן
        # העמודה בדרך כלל נקראת 'שם קרן' או 'NAME'
        column_name = 'NAME' if 'NAME' in df.columns else df.columns[1] 
        
        kosher_df = df[
            (df[column_name].str.contains('כספית', na=False)) & 
            (df[column_name].str.contains('כשרה|כשר', na=False))
        ].copy()

        # 2. ניקוי נתונים
        yield_col = 'YIELD_DAILY' if 'YIELD_DAILY' in df.columns else 'תשואה יומית'
        fee_col = 'MANAGEMENT_FEE' if 'MANAGEMENT_FEE' in df.columns else 'דמי ניהול'
        
        kosher_df[yield_col] = pd.to_numeric(kosher_df[yield_col], errors='coerce').fillna(0)
        kosher_df[fee_col] = pd.to_numeric(kosher_df[fee_col], errors='coerce').fillna(0)

        # 3. חישוב נטו
        kosher_df['NET_PROFIT'] = kosher_df[yield_col] - (kosher_df[fee_col] / 365)

        # 4. מציאת המנצחת
        winner = kosher_df.sort_values(by='NET_PROFIT', ascending=False).iloc[0]
        
        # התאמת שמות למסך הטלגרם
        result = {
            'NAME': winner[column_name],
            'NET_PROFIT': winner['NET_PROFIT'],
            'MANAGEMENT_FEE': winner[fee_col],
            'DATE': 'היום'
        }
        return result
    except Exception as e:
        print(f"Error logic: {e}")
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
