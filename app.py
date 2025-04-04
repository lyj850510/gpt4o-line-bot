from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
import os

app = Flask(__name__)

# 從環境變數讀取金鑰
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)

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
        user_msg = event.message.text
        print("[INFO] Received message from user:", user_msg)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": user_msg}
            ]
        )

        gpt_reply = response.choices[0].message.content.strip()
        print("[INFO] GPT-4o reply:", gpt_reply)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=gpt_reply)
        )
    except Exception as e:
        print("[ERROR] handle_message:", str(e))

if __name__ == "__main__":
    app.run(port=5000)
