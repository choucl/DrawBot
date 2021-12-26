from django.conf import settings
from transitions import Machine
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import  (
    MessageEvent,
    TextSendMessage,
    TemplateSendMessage,
    ButtonsTemplate,
    MessageTemplateAction
) 

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
hint_emoji = [
    {
        "index": 0,
        "productId": "5ac22b23040ab15980c9b44d",
        "emojiId": "022"
    }
]

class RobotMachine(object):

    def __init__(self, user_id):
        self.state = [
            {
                "name": "start",
                "on_enter": self._on_enter_start
            }, {
                "name": "ready",
                "on_enter": self._on_enter_ready
            }, {
                "name": "input",
                "on_enter": self._on_enter_input
            }, {
                "name": "color",
                "on_enter": self._on_enter_color
            }, {
                "name": "gen",
                "on_enter": self._on_enter_gen
            }
        ]
        self.user_id = user_id

        self.machine = Machine(
            model=self, 
            states=self.state,
            initial="start"
        )


        self.machine.add_transition("enter_type", "start", "ready")
        self.machine.add_transition("unrecognized", "start", "start")
        self.machine.add_transition("enter_relation", "ready", "input")
        self.machine.add_transition("unrecognized", "ready", "ready")
        self.machine.add_transition("enter_relation", "input", "color")
        self.machine.add_transition("unrecognized", "input", "input")
        self.machine.add_transition("enter_ok", "input", "gen")
        self.machine.add_transition("enter_color", "color", "input")
        self.machine.add_transition("unrecognized", "color", "color")
        self.machine.add_transition("enter_continue", "gen", "input")
        self.machine.add_transition("enter_restart", "gen", "start")

        self.graph_type = ""
        self.relations = []

    def _on_enter_start(self):
        print("enter start")
        line_bot_api.push_message(  # 回復傳入的訊息文字
            self.user_id,
            TemplateSendMessage(
                alt_text="Choose graph type",
                template=ButtonsTemplate(
                    title='Types',
                    text='Please choose the graph type',
                    actions=[
                        MessageTemplateAction(
                            label='Directional graph',
                            text='direction'
                        ),
                        MessageTemplateAction(
                            label='Undirectional graph',
                            text='undirection'
                        )
                    ]
                )
            )
        )

    def _on_enter_ready(self):
        print("enter ready")
        message = "Type " + self.graph_type + " chosen\nStart input relations:"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message)
        )
        message = \
            "$ Example: \n" \
            "node1 --> node2\n" \
            "node3 --edge-> node4"
        
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message, emojis=hint_emoji)
        )

    def _on_enter_input(self):
        print("enter input")

    def _on_enter_color(self):
        print("enter color")

    def _on_enter_gen(self):
        print("enter gen")
