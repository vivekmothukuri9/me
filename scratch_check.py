import urllib.request
import urllib.parse

bot_token = "8836944324:AAF9wPnqAUzPxJMaDhM9Jy_1H_oGFnZAYB4"
chat_id = "8999981074"
message_text = "Test message"
bot_name = "Nithya"

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
data = urllib.parse.urlencode({'chat_id': chat_id, 'text': f"💖 {bot_name}:\n\n{message_text}"}).encode('utf-8')
try:
    req = urllib.request.Request(url, data=data)
    response = urllib.request.urlopen(req)
    print("Success:", response.read().decode('utf-8'))
except Exception as e:
    print("Telegram error:", e)
    if hasattr(e, 'read'):
        print("Response:", e.read().decode('utf-8'))
