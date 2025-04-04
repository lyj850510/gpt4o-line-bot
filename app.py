from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
import os

app = Flask(__name__)

# 從環境變數取得金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)

# 基本問答對應
basic_responses = {
    "你好": "你好！我是你的數位桌遊設計助教，歡迎詢問任何關於桌遊設計的問題！",
    "嗨": "嗨嗨～需要設計數位桌遊的幫忙嗎？我可以提供主題、機制、規則等建議唷！",
    "你是誰": "我是專精於數位桌遊設計的助教，請儘管問我設計方面的問題吧！",
    "請問你會什麼": "我擅長提供數位桌遊的主題、機制、遊戲流程與設計建議喔！有什麼想法需要討論嗎？"
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
        print("[INFO] Received message:", user_msg)

        # 若為基本問題，直接回應（不呼叫 GPT）
        for keyword in basic_responses:
            if keyword in user_msg:
                reply = basic_responses[keyword]
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply)
                )
                return

        # GPT-4o 處理數位桌遊相關問題
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一位專精於數位桌遊設計的顧問。請只回答與數位桌遊設計相關的問題，"
                        "例如：遊戲機制、規則設計、主題創意、數位轉化建議等。"
                        "對於與主題無關的問題，請回覆：『抱歉這不是我的專業，我專門回答與數位桌遊設計相關的問題喔！』。"
                        "請將回答控制在 250 字以內。"
                    )
                },
                {"role": "user", "content": user_msg}
            ]
        )

        gpt_reply = response.choices[0].message.content.strip()

        # 限制長度（保險再裁切一次，避免 GPT 失控）
        if len(gpt_reply) > 200:
            gpt_reply = gpt_reply[:197] + "..."

        print("[INFO] GPT-4o reply:", gpt_reply)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=gpt_reply)
        )

    except Exception as e:
        print("[ERROR] handle_message:", str(e))

if __name__ == "__main__":
    app.run(port=5000)
