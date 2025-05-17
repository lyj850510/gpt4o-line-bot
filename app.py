from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
from sheet_logger import log_conversation
import os

app = Flask(__name__)

# 金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)

# 使用者上下文記憶
user_sessions = {}

# 特權使用者白名單
whitelist_users = {"U68ce099aa6425357d147da260811be84"}

# 基本問答
basic_responses = {
    "你好": "你好！我是你的數位桌遊設計助教，歡迎詢問任何關於桌遊設計的問題！",
    "嗨": "嗨嗨～需要設計數位桌遊的幫忙嗎？我可以提供主題、機制、規則等建議唷！",
    "你是誰": "我是專精於數位桌遊設計的助教，請儘管問我設計方面的問題吧！",
    "你會什麼": "我擅長提供數位桌遊的主題、機制、遊戲流程與設計建議喔！有什麼想法需要討論嗎？"
}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("[ERROR] Invalid Signature")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_msg = event.message.text.strip()
        user_id = event.source.user_id
        print(f"[INFO] [{user_id}] {user_msg}")

        # 基本問答
        for keyword in basic_responses:
            if keyword in user_msg:
                reply = basic_responses[keyword]
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply)
                )
                log_conversation(user_id, user_msg, reply)
                return

        # 初始化使用者上下文
        if user_id not in user_sessions:
            user_sessions[user_id] = []

        # 準備訊息串
        history = user_sessions[user_id][-10:]
        history.append({"role": "user", "content": user_msg})

        # 根據 user_id 使用不同的 system prompt
        if user_id in whitelist_users:
            system_prompt = {
                "role": "system",
                "content": (
                    "你是一位智慧且樂於助人的 AI 助理，可以回答任何問題，請自然且清楚地回覆使用者問題。"
                )
            }
        else:
            system_prompt = {
                "role": "system",
                "content": (
                    "你是一位擅長數位桌遊設計與 AI 繪圖的顧問，能協助使用者進行數位桌遊創作，"
                    "包含主題發想、規則設計、遊戲機制與轉化工具等。請盡量將回覆聚焦在這些主題上，"
                    "若問題完全與本專業無關，請委婉說明。針對提問方式（如希望用條列、希望精簡），請正常回應即可，"
                    "不要誤判為主題無關。每次回覆請控制在 200 個中文字內，自然結尾。"
                )
            }

        messages = [system_prompt] + history


        # 呼叫 GPT
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=300  # ≈ 約 200～250 個中文字
        )

        gpt_reply = response.choices[0].message.content.strip()

        if len(gpt_reply) > 200:
            gpt_reply = gpt_reply[:197] + "..."

        # 記憶對話
        user_sessions[user_id].append({"role": "user", "content": user_msg})
        user_sessions[user_id].append({"role": "assistant", "content": gpt_reply})
        user_sessions[user_id] = user_sessions[user_id][-10:]

        # 回傳
        print(f"[GPT] [{user_id}] {gpt_reply}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=gpt_reply)
        )

        # 紀錄到 Google Sheet
        log_conversation(user_id, user_msg, gpt_reply)

    except Exception as e:
        print("[ERROR] handle_message:", str(e))

# 支援 Render 的 PORT 綁定
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
