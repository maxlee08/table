from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pymysql.cursors
import os
import logging
import traceback

# 設定日誌配置
logging.basicConfig(level=logging.DEBUG)  # 設置為 DEBUG 以便記錄更多信息
app = Flask(__name__)

# LINE API 配置
line_bot_api = LineBotApi('iwDXOBNGbSA02uFDBxiLiempxEtVDtFWTUoSyiTaQZqGHo8IRywesd3TsuckYuBKzL6ID0YdvCyiijQhM9m7QA38JYP1lmmJf2IpmnQOUfntpiIOWhJ5QPYmekUBmyzi3A0IdyWJItTGeV67Yt8z7gdB04t89/1O/w1cDnyilFU=')  # 替換為您的 CHANNEL_ACCESS_TOKEN
handler = WebhookHandler('ed84881ce5a0fcabbd639ee023940ad6')  # 替換為您的 CHANNEL_SECRET

# 資料庫連線配置
db_config = {
    'host': '114.35.141.12',  # 使用公共 IP
    'user': 'Max',
    'password': 'table0813',  # 替換為您的資料庫密碼
    'db': 'table0814',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 固定的用戶 ID，假設該用戶是唯一的
USER_ID = 'U41c59545fe9b0a790446e46dedee4d92'  # 這應該是您指定的唯一用戶 ID

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
    response_text = ""  # 預設的回應文字

    # 確保來自 LINE 的訊息是來自唯一的用戶
    if event.source.user_id != USER_ID:
        response_text = "抱歉，這個服務只對指定用戶開放。"
        try:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
        except Exception as e:
            error_message = f"發送錯誤訊息時發生錯誤: {str(e)}\n{traceback.format_exc()}"
            app.logger.error(error_message)
        return

    # 連線至 MySQL 資料庫
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # 根據使用者輸入的內容查詢資料
            if user_message == "查詢電費":
                try:
                    cursor.execute("SELECT * FROM electricity_usage WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (USER_ID,))
                    result = cursor.fetchone()
                    app.logger.debug(f"查詢結果: {result}")  # 記錄查詢結果
                    
                    if result:
                        response_text = f"您的最近一次用電量為 {result['usage_kwh']} kWh，電費為 {result['bill_amount']} 元。"
                    else:
                        response_text = "找不到您的用電紀錄。"
                except Exception as e:
                    error_message = f"查詢電費資料庫錯誤: {str(e)}\n{traceback.format_exc()}"
                    app.logger.error(error_message)
                    response_text = "抱歉，查詢電費時發生錯誤，請稍後再試。"

            elif user_message == "查詢用電紀錄":
                try:
                    cursor.execute("SELECT * FROM electricity_usage WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (USER_ID,))
                    results = cursor.fetchall()
                    app.logger.debug(f"查詢紀錄結果: {results}")  # 記錄查詢結果
                    
                    if results:
                        records = "\n".join([f"用電量: {row['usage_kwh']} kWh, 電費: {row['bill_amount']} 元, 日期: {row['created_at']}" for row in results])
                        response_text = f"您的最近 5 筆用電紀錄:\n{records}"
                    else:
                        response_text = "找不到您的用電紀錄。"
                except Exception as e:
                    error_message = f"查詢用電紀錄資料庫錯誤: {str(e)}\n{traceback.format_exc()}"
                    app.logger.error(error_message)
                    response_text = "抱歉，查詢用電紀錄時發生錯誤，請稍後再試。"

            else:
                response_text = "請輸入 '查詢電費' 或 '查詢用電紀錄' 來查詢資料。"

        # 傳送回應給使用者
        try:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
        except Exception as e:
            error_message = f"發送回應訊息錯誤: {str(e)}\n{traceback.format_exc()}"
            app.logger.error(error_message)
    
    except Exception as e:
        error_message = f"處理訊息時發生錯誤: {str(e)}\n{traceback.format_exc()}"
        app.logger.error(error_message)
        response_text = "抱歉，發生了一些錯誤，請稍後再試。"
        try:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
        except Exception as reply_error:
            error_message = f"發送錯誤訊息時發生錯誤: {str(reply_error)}\n{traceback.format_exc()}"
            app.logger.error(error_message)
    
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
