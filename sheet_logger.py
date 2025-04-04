import gspread
import json
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_NAME = "L101TA"
SHEET_NAME = "工作表1"

def init_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # 將 GOOGLE_CREDS_JSON 字串轉成 dict
    creds_dict = json.loads(os.environ.get("GOOGLE_CREDS_JSON"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)
    return sheet

def log_conversation(user_id, user_msg, bot_reply):
    try:
        sheet = init_sheet()
        timestamp = datetime.now().isoformat()
        sheet.append_row([timestamp, user_id, user_msg, bot_reply])
        print(f"[SHEET] Logged message from {user_id}")
    except Exception as e:
        print(f"[SHEET ERROR] {e}")
