from django.conf import settings
from transitions import Machine
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import  (
    MessageEvent,
    TextSendMessage,
    TemplateSendMessage,
    ImageSendMessage,
    ButtonsTemplate,
    MessageTemplateAction
) 

from graphviz import Graph, Digraph
import pyimgur
import os

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
                "name": "node1",
                "on_enter": self._on_enter_node1
            }, {
                "name": "node2",
                "on_enter": self._on_enter_node2
            }, {
                "name": "label",
                "on_enter": self._on_enter_label
            }, {
                "name": "other",
                "on_enter": self._on_enter_other
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

        self.machine.add_transition("enter_type",     "start", "ready")
        self.machine.add_transition("unrecognized",   "start", "start")
        self.machine.add_transition("enter_relation", "ready", "input")
        self.machine.add_transition("unrecognized",   "ready", "ready")
        self.machine.add_transition("enter_node",     "ready", "node1")
        self.machine.add_transition("enter_node",     "node1", "node2")
        self.machine.add_transition("enter_yes",      "node2", "label")
        self.machine.add_transition("enter_no",       "node2", "other")
        self.machine.add_transition("enter_label",    "label", "other")
        self.machine.add_transition("enter_yes",      "other", "node1")
        self.machine.add_transition("enter_no",       "other", "input")
        self.machine.add_transition("enter_relation", "input", "input")
        self.machine.add_transition("enter_node",     "input", "node1")
        self.machine.add_transition("unrecognized",   "input", "input")
        self.machine.add_transition("enter_ok",       "input", "gen")
        self.machine.add_transition("enter_continue", "gen",   "input")
        self.machine.add_transition("enter_restart",  "gen",   "start")

        self.graph_type = ""
        self.cur_relation = ["", "", ""]
        self.relations = []

    def _on_enter_start(self):
        print("enter start")
        line_bot_api.push_message(
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
                            label='Indirectional graph',
                            text='indirection'
                        )
                    ]
                )
            )
        )

    def _on_enter_ready(self):
        print("enter ready")
        message = "Type " + self.graph_type + " chosen\nStart input first node!"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message)
        )
        message = \
            "$ You could also use these instructions to construct relations: \n" \
            "- node1 --> node2\n" \
            "- node3 --edge-> node4" \
        
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message, emojis=hint_emoji)
        )

    def _on_enter_node1(self):
        print("enter node1")
        message = "Enter the second node:"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message)
        )
    
    def _on_enter_node2(self):
        print("enter node2")
        line_bot_api.push_message(
            self.user_id,
            TemplateSendMessage(
                alt_text="If label name?",
                template=ButtonsTemplate(
                    title='Any label name?',
                    text="Any label name for relation?",
                    actions=[
                        MessageTemplateAction(
                            label='Yes',
                            text='yes'
                        ),
                        MessageTemplateAction(
                            label='No',
                            text='no'
                        )
                    ]
                )
            )
        )

    def _on_enter_label(self):
        print("enter label")
        message = "Enter the label for relation:"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message)
        )

    def _on_enter_other(self):
        print("enter other")
        line_bot_api.push_message(
            self.user_id,
            TemplateSendMessage(
                alt_text="Other node?",
                template=ButtonsTemplate(
                    title='Other node',
                    text="Any other node from the first node?",
                    actions=[
                        MessageTemplateAction(
                            label='Yes',
                            text='yes'
                        ),
                        MessageTemplateAction(
                            label='No',
                            text='no'
                        )
                    ]
                )
            )
        )


    def _on_enter_input(self):
        print("enter input")
        message = "$ Current Input status:"
        for element in self.relations:
            message += "\n" + element[0] + " --> " + element[1]
            if (element[2] != ""):
                message += " (edge: " + element[2] + ")"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message, emojis=hint_emoji)
        )
        message = "Enter the next node or ok to generate graph:\n"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message)
        )
        message = \
            "$ You could also use these instructions to construct relations: \n" \
            "- node1 --> node2\n" \
            "- node3 --edge-> node4"
        line_bot_api.push_message(
            self.user_id,
            TextSendMessage(message, emojis=hint_emoji)
        )



    def _on_enter_gen(self):
        print("enter gen")
        if self.graph_type == "direction":
            graph = Digraph()
        else:
            graph = Graph()
        for relation in self.relations:
            print(relation)
            graph.node(relation[0], relation[0])
            graph.node(relation[1], relation[1])
            if (relation[2] != ""):
                graph.edge(relation[0], relation[1], relation[2])
            else: 
                graph.edge(relation[0], relation[1])
        graph.format = "png"
        graph.render(self.user_id, view=False)
        print("render successfully")
        im = pyimgur.Imgur(settings.IMGUR_CLIENT_ID)
        path = self.user_id + ".png"
        uploaded_image = im.upload_image(path)
        line_bot_api.push_message(
            self.user_id,
            ImageSendMessage(
                original_content_url=uploaded_image.link,
                preview_image_url=uploaded_image.link
            )
        )

        line_bot_api.push_message(
            self.user_id,
            TemplateSendMessage(
                alt_text="What's next?",
                template=ButtonsTemplate(
                    title='Next behavior',
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
