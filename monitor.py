import os
import requests
import pandas as pd
import io

def get_top_kosher_fund():
    # כתובת ההורדה הישירה (שראינו שעובדת ועוקפת את החסימות)
    url = "https://data.gov.il/datastore/dump/e6fce050-705d-4f05-9502-0e23805494d9"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("מוריד את קובץ הנתונים הגולמי...")
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # --- תיקון הקסם לעברית ---
        # מנסים לקרוא כ-UTF-8, אם נכשל מנסים Windows-1255 (הנפוץ בממשלה)
        try:
            content = response.content.decode('utf-8-sig')
        except UnicodeDecodeError:
            content = response.content.decode('cp1255')
            
        df = pd.read_csv(io.StringIO(content))
        
        # ניקוי שמות עמודות (מסיר רווחים מיותרים)
        df.columns = df.columns.str.strip()
        
        # הדפסת שמות העמודות ללוג כדי שנוכל לראות אם זה הצליח
        print(f"עמודות שנמצאו: {list(df.columns)}")

        # איתור עמודות גמיש
        col_name = next((c for c in df.columns if any(k in c for k in ['שם', 'NAME', 'קרן'])), None)
        col_yield = next((c for c in df.columns if any(k in c for k in ['תשואה', 'YIELD', 'יומית'])), None)
        col_fee = next((c for c in df.columns if any(k in c for k in ['ניהול', 'FEE', 'שכ"נ'])), None)

        if not col_name:
            print("שגיאה: לא נמצאה עמודת שם קרן.")
            return None

        # המרה לטקסט וסינון
        df[col_name] = df[col_name].astype(str)
        
        # סינון רחב: מחפש "כספית" וגם ("כשר" או "מהדרין")
        kosher_df = df[
            (df[col_name].str.contains('כספית', na=False)) & 
            (df[col_name].str.contains('כשר|מהדרין', na=False))
        ].copy()

        print(f"נמצאו {len(kosher_df)} קרנות כספיות כשרות.")

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
        print(f"שגיאה בתהליך: {e}")
        return None

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
    result = get_top_kosher_fund()
    if result:
        send_to_telegram(result)
        print("הודעה נשלחה בהצלחה!")
