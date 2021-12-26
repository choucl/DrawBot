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
            user_id = event.source.user_id
            # check if is new user and initiate
            if (not event.source.user_id in user_map):
                user_map[user_id] = RobotMachine(user_id)

            if (user_map[user_id].is_start()):
                # start state
                start_transition(event, user_id)
            elif (user_map[user_id].is_ready()):
                # graph type state
                ready_transition(event, user_id)
            #elif (user_map[user_id]["state"] == 2):
            #    # state for input node-edge relation
            #    input_state(event, user_id)
            #elif (user_map[user_id]["state"] == 3):
            #    # state for choosing if the last input need to be colored
            #    if_color_state(event, user_id) 
            #elif (user_map[user_id]["state"] == 4):
            #    # pick color for element 
            #    pick_color_state(event, user_id)
            #elif (user_map[user_id]["state"] == 5):
            #    # generate image state
            #    gen_img_state(event, user_id)

            #if isinstance(event, MessageEvent):  # checked if is text event
            #    line_bot_api.reply_message(  #  echo the text passed in
            #        event.reply_token,
            #        TextSendMessage(text=event.message.text)
            #    )
                    
        return HttpResponse()
    else:
        return HttpResponseBadRequest()

def gen_msg(user_id):
    return_txt = "Current input:\n"
    for info in user_map[user_id]:
        return_txt += info[0] + " --> " + info[1]
        if info[2] != "":
            return_txt += " (edge: " + info[2] + ")"
        return_txt += "\n"
    return return_txt[:-1]

# parse the user input string
# input: string
# output: tuple, (success or not, tokenize result)
def parse(str):
    split = str.split()
    if (split[0].lower() == 'ok'):
        return (True, ("ok"))
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
    elif (event.message.text.lower() == 'undirection'):
        user_map[user_id].graph_type = 'undirection'
        user_map[user_id].enter_type()
    else:
        message = "Unrecogized graph type\nPlease choose directional or undirectional graph"
        user_map[user_id].unrecognized()
        if isinstance(event, MessageEvent):  # checked if is text event
            line_bot_api.reply_message(  #  echo the text passed in
                event.reply_token,
                TextSendMessage(text=message)
            )
        

def ready_transition(event, user_id):
    message = ""
    parse_result = parse(event.message.text)
    if (parse_result[0]):
        user_map[user_id].relations.append(parse_result[1])
        user_map[user_id].enter_relation()
    else:
        message = "Unrecognized input\nPlease input again!"
        if isinstance(event, MessageEvent):  # checked if is text event
            line_bot_api.reply_message(  #  echo the text passed in
                event.reply_token,
                TextSendMessage(text=message)
            )

