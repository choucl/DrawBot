from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
 
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage
# Create your views here.


line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
user_map = {}

@csrf_exempt
def callback(request):
 
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
 
        try:
            events = parser.parse(body, signature)  # passed in events
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()
 
        for event in events: 
            print(event.source)
            print(event.source.user_id)
            if not event.source.user_id in user_map:
                user_map[event.source.user_id] = [event.message.text]
            else:
                user_map[event.source.user_id].append(event.message.text)

            message = gen_msg(event.source.user_id)
            if isinstance(event, MessageEvent):  # checked if is text event
                line_bot_api.reply_message(  #  echo the text passed in
                    event.reply_token,
                    TextSendMessage(text=message)
                )
                    
        return HttpResponse()
    else:
        return HttpResponseBadRequest()

def gen_msg(user_id):
    return_txt = ""
    for text in user_map[user_id]:
        return_txt += text + "\n"
    return return_txt
