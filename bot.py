from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pymysql.cursors
import os

# 初始化 Flask 應用程式
app = Flask(__name__)

# LINE API 配置
line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')  # 替換為您的 CHANNEL_ACCESS_TOKEN
handler = WebhookHandler('YOUR_CHANNEL_SECRET')  # 替換為您的 CHANNEL_SECRET

# 資料庫連線配置
db_config = {
    'host': '114.35.141.12',  # 使用公共 IP
    'user': 'Max',
    'password': 'table0813',  # 替換為您的資料庫密碼
    'db': 'table0813',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

@app.route("/callback", methods=['POST'])
def callback():
    # 驗證 LINE Webhook 請求
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Received request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature detected")
        abort(400)

    return 'OK'

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.strip()
    line_user_id = event.source.user_id  # 取得 LINE 用戶的 user_id

    # 取得 LINE 用戶的資料（例如顯示名稱）
    try:
        profile = line_bot_api.get_profile(line_user_id)
        line_user_name = profile.display_name  # 用戶的顯示名稱
        line_user_picture = profile.picture_url  # 用戶的頭像 URL
    except Exception as e:
        app.logger.error(f"無法取得用戶資料: {e}")
        line_user_name = "用戶"
        line_user_picture = None

    # 連線至 MySQL 資料庫
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # 如果該用戶還未存在，則插入資料
            cursor.execute("SELECT * FROM users WHERE user_id=%s", (line_user_id,))
            user = cursor.fetchone()

            if not user:
                # 如果用戶不存在，插入新用戶資料
                cursor.execute("INSERT INTO users (user_id, user_name) VALUES (%s, %s)", (line_user_id, line_user_name))
                connection.commit()

            # 處理用戶訊息
            if user_message == "查詢電費":
                cursor.execute("SELECT * FROM electricity_usage WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (line_user_id,))
                result = cursor.fetchone()
                
                if result:
                    response_text = f"您的最近一次用電量為 {result['usage_kwh']} kWh，電費為 {result['bill_amount']} 元。"
                else:
                    response_text = "找不到您的用電紀錄。"

            elif user_message == "查詢用電紀錄":
                cursor.execute("SELECT * FROM electricity_usage WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (line_user_id,))
                results = cursor.fetchall()
                
                if results:
                    records = "\n".join([f"用電量: {row['usage_kwh']} kWh, 電費: {row['bill_amount']} 元, 日期: {row['created_at']}" for row in results])
                    response_text = f"您的最近 5 筆用電紀錄:\n{records}"
                else:
                    response_text = "找不到您的用電紀錄。"
            else:
                response_text = "請輸入 '查詢電費' 或 '查詢用電紀錄' 來查詢資料。"

        # 傳送回應給使用者
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
    
    except Exception as e:
        app.logger.error(f"資料庫查詢錯誤: {e}")
        response_text = "抱歉，發生了一些錯誤，請稍後再試。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
    
    finally:
        connection.close()

# 新增根路由，避免 404 錯誤
@app.route('/')
def home():
    return "Flask bot is running!"

# 啟動 Flask 應用程式
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # 使用 Render 自動設定的端口
    app.run(host="0.0.0.0", port=port, debug=True)
