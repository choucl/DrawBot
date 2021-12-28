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
                user_map[user_id].get_graph().draw('my_state_diagram.png', prog='dot')

            user_map[user_id].reply_token = event.reply_token
            if (user_map[user_id].is_start()):
                # start state
                start_transition(event, user_id)
            elif (user_map[user_id].is_ready()):
                # graph type state
                input_transition(event, user_id, 0)
            elif (user_map[user_id].is_node1()):
                # graph type state
               set_cur_transition(event, user_id, 1)
            elif (user_map[user_id].is_node2()):
                # graph type state
                yes_no_transition(event, user_id)
                if (user_map[user_id].is_other()):
                    user_map[user_id].relations.append(user_map[user_id].cur_relation[:])
            elif (user_map[user_id].is_label()):
                # graph type state
               set_cur_transition(event, user_id, 2)
            elif (user_map[user_id].is_other()):
                # graph type state
               yes_no_transition(event, user_id)
               user_map[user_id].cur_relation[2] = ""
            elif (user_map[user_id].is_input()):
                # state for input node-edge relation
                input_transition(event, user_id, 1)
            elif (user_map[user_id].is_gen()):
                # state for choosing if the last input need to be colored
                gen_transition(event, user_id)
                    
        return HttpResponse()
    else:
        return HttpResponseBadRequest()


def parse(str):
    split = str.split("\n")
    parse_result = []
    parse_state = ""
    if (len(split) > 1):
        for line in split:
            tmp = line_parse(line)
            if tmp[0] == False:
                return ("error", [])
            else:
                parse_result.append(tmp)
        parse_state = "relation"
    else:
        tmp = line_parse(str)
        if (tmp[0]):
            parse_result.append(tmp)
            parse_state = "relation"
        else:
            parse_result.append(tmp)
            parse_state = "node"
    return (parse_state, parse_result)


# parse the user input string
# input: string
# output: tuple, (success or not, tokenize result)
def line_parse(str):
    split = str.split()
    if len(split) != 3:
        return (False, ())
    else:
        if (split[1] == '->'):
            return (True, (split[0], split[2], ""))
        elif (split[1][:1] == '-' and split[1][-1:] == '>'):
            return (True, (split[0], split[2], split[1][2:-2]))
        else:
            return (False, ())

def start_transition(event, user_id):
    message = ""
    if (event.message.text.lower() == 'directed'):
        user_map[user_id].graph_type = 'directed' 
        user_map[user_id].enter_type()
    elif (event.message.text.lower() == 'undirected'):
        user_map[user_id].graph_type = 'undirected'
        user_map[user_id].enter_type()
    else:
        message = "$ Unrecogized graph type\nPlease choose directed or undirected graph"
        user_map[user_id].message_q.append(TextSendMessage(text=message, emojis=cross_emoji))
        user_map[user_id].unrecognized()
        
def set_cur_transition(event, user_id, pos):
    user_map[user_id].cur_relation[pos] = event.message.text 
    if (pos == 2):
        user_map[user_id].enter_label()
        user_map[user_id].relations.append(user_map[user_id].cur_relation[:])
    else:
        user_map[user_id].enter_node()

def yes_no_transition(event, user_id):
    message = ""
    print(event.message.text.lower())
    if (event.message.text.lower() == 'yes'):
        user_map[user_id].enter_yes()
    elif (event.message.text.lower() == 'no'):
        user_map[user_id].enter_no()
    else:
        message = "$ Unrecogized input\nPlease choose yes or no"
        user_map[user_id].message_q.append(TextSendMessage(text=message, emojis=cross_emoji))
        user_map[user_id].unrecognized()

def input_transition(event, user_id, is_ready):
    if (is_ready and event.message.text.lower() == "ok"):
        user_map[user_id].enter_ok()
        return
    parse_result = parse(event.message.text)
    if (parse_result[0] == "relation"):
        for result in parse_result[1]:
            user_map[user_id].relations.append(result[1])
        user_map[user_id].enter_relation()
    elif (parse_result[0] == "node"):
        user_map[user_id].cur_relation[0] = event.message.text 
        user_map[user_id].enter_node()
    else:
        message = "$ Unrecognized input\nPlease input again!"
        user_map[user_id].message_q.append(TextSendMessage(text=message, emojis=cross_emoji))
        user_map[user_id].unrecognized()

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
        user_map[user_id].message_q.append(TextSendMessage(text=message, emojis=cross_emoji))
        user_map[user_id].message_q.append(
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
