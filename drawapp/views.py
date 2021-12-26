from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
 
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import  (
    MessageEvent,
    TextSendMessage,
    TemplateSendMessage,
    ButtonsTemplate,
    MessageTemplateAction
) 

from drawapp.machine import RobotMachine
# Create your views here.


line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
user_map = {}
cross_emoji = [
    {
        "index": 0,
        "productId": "5ac21a18040ab15980c9b43e",
        "emojiId": "068"
    }
]

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
            print(event.source.type)
            if (event.source.type == "group"):
                user_id = event.source.group_id
            else:
                user_id = event.source.user_id
            # check if is new user and initiate
            if (not user_id in user_map):
                user_map[user_id] = RobotMachine(user_id)

            if (user_map[user_id].is_start()):
                # start state
                start_transition(event, user_id)
            elif (user_map[user_id].is_ready()):
                # graph type state
                input_transition(event, user_id, 0)
            elif (user_map[user_id].is_input()):
                # state for input node-edge relation
                input_transition(event, user_id, 1)
            elif (user_map[user_id].is_gen()):
                # state for choosing if the last input need to be colored
                gen_transition(event, user_id)
                    
        return HttpResponse()
    else:
        return HttpResponseBadRequest()


# parse the user input string
# input: string
# output: tuple, (success or not, tokenize result)
def parse(str):
    split = str.split()
    if len(split) != 3:
        return (False, ())
    else:
        if (split[1] == '-->'):
            return (True, (split[0], split[2], ""))
        elif (split[1][:2] == '--' and split[1][-2:] == '->'):
            return (True, (split[0], split[2], split[1][2:-2]))
        else:
            return (False, ())

def start_transition(event, user_id):
    message = ""
    if (event.message.text.lower() == 'direction'):
        user_map[user_id].graph_type = 'direction' 
        user_map[user_id].enter_type()
        return
    elif (event.message.text.lower() == 'undirection'):
        user_map[user_id].graph_type = 'undirection'
        user_map[user_id].enter_type()
        return

    user_map[user_id].unrecognized()
    message = "$ Unrecogized graph type\nPlease choose directional or undirectional graph"
    if isinstance(event, MessageEvent):  # checked if is text event
        line_bot_api.reply_message(  #  echo the text passed in
            event.reply_token,
            TextSendMessage(text=message, emojis = cross_emoji)
        )
        
def input_transition(event, user_id, has_input):
    if (has_input and event.message.text.lower() == "ok"):
        user_map[user_id].enter_ok()
        return
    parse_result = parse(event.message.text)
    if (parse_result[0]):
        user_map[user_id].relations.append(parse_result[1])
        user_map[user_id].enter_relation()
    else:
        message = "$ Unrecognized input\nPlease input again!"
        if isinstance(event, MessageEvent):  # checked if is text event
            line_bot_api.reply_message(  #  echo the text passed in
                event.reply_token,
                TextSendMessage(text=message, emojis = cross_emoji)
            )

def gen_transition(event, user_id):
    if (event.message.text.lower() == "continue"):
        user_map[user_id].enter_continue()
        return
    elif (event.message.text.lower() == "restart"):
        user_map[user_id].enter_restart()
        user_map[user_id].graph_type = ""
        user_map[user_id].relations = []
        return
    else:
        message = "$ Unrecognized input\nPlease input again!"
        if isinstance(event, MessageEvent):  # checked if is text event
            line_bot_api.reply_message(  #  echo the text passed in
                event.reply_token,
                TextSendMessage(text=message, emojis = cross_emoji)
            )
            line_bot_api.push_message(  # 回復傳入的訊息文字
                user_id,
                TemplateSendMessage(
                    alt_text="What's next?",
                    template=ButtonsTemplate(
                        title='Types',
                        text="What's next?",
                        actions=[
                            MessageTemplateAction(
                                label='Continue',
                                text='continue'
                            ),
                            MessageTemplateAction(
                                label='Restart',
                                text='restart'
                            )
                        ]
                    )
                )
            )
