from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pymysql.cursors

# 初始化 Flask 應用程式
app = Flask(__name__)

# LINE API 配置
line_bot_api = LineBotApi('iwDXOBNGbSA02uFDBxiLiempxEtVDtFWTUoSyiTaQZqGHo8IRywesd3TsuckYuBKzL6ID0YdvCyiijQhM9m7QA38JYP1lmmJf2IpmnQOUfntpiIOWhJ5QPYmekUBmyzi3A0IdyWJItTGeV67Yt8z7gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('ed84881ce5a0fcabbd639ee023940ad6')

# MySQL 資料庫連線配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'db': 'table0813',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# /callback 路由，用於接收 LINE Webhook 請求
@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭
    signature = request.headers['X-Line-Signature']

    # 取得訊息主體
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 驗證 Webhook
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.strip()

    # 連線至 MySQL 資料庫
    connection = pymysql.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            # 根據使用者輸入的內容查詢資料
            if user_message == "查詢電費":
                cursor.execute("SELECT * FROM electricity_usage WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (event.source.user_id,))
                result = cursor.fetchone()
                
                if result:
                    response_text = f"您的最近一次用電量為 {result['usage_kwh']} kWh，電費為 {result['bill_amount']} 元。"
                else:
                    response_text = "找不到您的用電紀錄。"

            elif user_message == "查詢用電紀錄":
                cursor.execute("SELECT * FROM electricity_usage WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (event.source.user_id,))
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

# 啟動 Flask 應用程式
if __name__ == "__main__":
    app.run(port=8000)
