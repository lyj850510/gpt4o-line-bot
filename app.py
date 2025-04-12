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

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位擅長數位桌遊設計與 AI 繪圖的顧問，能協助使用者進行數位桌遊創作，包含主題發想、規則設計、遊戲機制與轉化工具等。請盡量將回覆聚焦在這些主題上，若問題完全與本專業無關，請委婉說明。針對提問方式（如希望用條列、希望精簡），請正常回應即可，不要誤判為主題無關。"
                    "數位桌遊設計例如：遊戲機制、規則設計、主題創意、數位轉化建議等；"
                    "工具像是：playingcard.io；AI繪圖例如：工具介紹、提詞(Prompt)使用與建議等。"
                    "對於與主題無關的問題，請回覆：『抱歉，這不是我的專業，我專門回答與數位桌遊設計相關的問題喔！』。"
                    "請將每次回答控制在 200 個中文字以內，並用條列式清楚說明重點，請僅簡要列出 3~4 個重點，不要展開太多細節，並請在回答結尾時自然結束，務必不要中途被截斷導致對話沒有收尾"
                )
            }
        ] + history

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
