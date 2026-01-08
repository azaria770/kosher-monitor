import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # הדבק כאן את הקישור שקיבלת מ-Google Sheets (Publish to web)
    url = "הקישור_שלך_כאן"
    
    try:
        print("מושך נתונים מעובדים משרת הגיבוי...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # קריאת הנתונים
        df = pd.read_csv(io.StringIO(response.text))
        
        # איתור עמודות גמיש (תומך בעברית)
        col_name = next((c for c in df.columns if 'שם' in str(c) or 'NAME' in str(c).upper()), None)
        col_yield = next((c for c in df.columns if 'תשואה' in str(c) or 'YIELD' in str(c).upper()), None)
        col_fee = next((c for c in df.columns if 'ניהול' in str(c) or 'FEE' in str(c).upper()), None)

        # סינון קרנות כשרות
        df[col_name] = df[col_name].astype(str)
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר', na=False))
        ].copy()

        if kosher_df.empty:
            print("לא נמצאו קרנות כשרות.")
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
        print(f"שגיאת מערכת: {e}")
        return None

# פונקציית הטלגרם נשארת ללא שינוי...
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
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    data = get_top_kosher_fund()
    if data:
        send_to_telegram(data)
        print("הודעה נשלחה בהצלחה!")
