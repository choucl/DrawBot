from django.conf import settings
from transitions.extensions import GraphMachine
from linebot import LineBotApi, WebhookParser
from linebot.models import  (
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
                "name": "dir",
                "on_enter": self._on_enter_dir
            }, {
                "name": "ready",
                "on_enter": self._on_enter_ready
            }, {
                "name": "input",
                "on_enter": self._on_enter_input
            }, {
                "name": "delete",
                "on_enter": self._on_enter_delete
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

        self.machine = GraphMachine(
            model=self, 
            states=self.state,
            initial="start"
        )

        self.machine.add_transition("enter_type",     "start", "dir")
        self.machine.add_transition("unrecognized",   "start", "start")
        self.machine.add_transition("enter_dir",      "dir",   "ready")
        self.machine.add_transition("unrecognized",   "dir",   "dir")
        self.machine.add_transition("enter_input",    "ready", "input")
        self.machine.add_transition("enter_generate", "ready", "gen")
        self.machine.add_transition("enter_del",      "ready", "delete")
        self.machine.add_transition("unrecognized",   "ready", "ready")
        self.machine.add_transition("enter_number",   "delete", "ready")
        self.machine.add_transition("unrecognized",   "delete", "delete")
        self.machine.add_transition("enter_node",     "ready", "node1")
        self.machine.add_transition("enter_node",     "node1", "node2")
        self.machine.add_transition("enter_yes",      "node2", "label")
        self.machine.add_transition("enter_no",       "node2", "other")
        self.machine.add_transition("unrecognized",   "node2", "node2")
        self.machine.add_transition("enter_label",    "label", "other")
        self.machine.add_transition("enter_yes",      "other", "node1")
        self.machine.add_transition("enter_no",       "other", "ready")
        self.machine.add_transition("unrecognized",   "other", "other")
        self.machine.add_transition("enter_relation", "input", "ready")
        self.machine.add_transition("enter_node",     "input", "node1")
        self.machine.add_transition("enter_continue", "gen",   "ready")
        self.machine.add_transition("unrecognized",   "input", "input")
        self.machine.add_transition("enter_restart",  "gen",   "start")

        self.reply_token = ""
        self.graph_type = ""
        self.graph_dir = ""
        self.cur_relation = ["", "", ""]
        self.relations = []
        self.message_q = []

    def line_bot_reply(self):
        line_bot_api.reply_message(
            self.reply_token,
            self.message_q
        )
        self.message_q = []

    def get_cur_relation(self):
        message = "$ Current Input status:"
        count = 1
        for element in self.relations:
            message += "\n" + str(count) + ".  " + element[0]
            if (element[2] != ""):
                message += " -" + element[2] + "> "
            else:
                message += " -> "
            message +=  element[1]
            count += 1
        if (len(self.relations) == 0):
            message += "\n(none)"
        return message


    def _on_enter_start(self):
        print("enter start")
        self.message_q.append(
            TemplateSendMessage(
                alt_text="Choose graph type",
                template=ButtonsTemplate(
                    title='Types',
                    text='Please choose the graph type',
                    actions=[
                        MessageTemplateAction(
                            label='Directed graph',
                            text='directed'
                        ),
                        MessageTemplateAction(
                            label='Undirected graph',
                            text='undirected'
                        )
                    ]
                )
            )
        )
        self.line_bot_reply()

    def _on_enter_dir(self):
        print("enter dir")
        self.message_q.append(
            TemplateSendMessage(
                alt_text="Choose graph direction",
                template=ButtonsTemplate(
                    title='Direction',
                    text='Please choose the direction of the graph',
                    actions=[
                        MessageTemplateAction(
                            label='Top-Down',
                            text='TD'
                        ),
                        MessageTemplateAction(
                            label='Left-Right',
                            text='LR'
                        )
                    ]
                )
            )
        )
        self.line_bot_reply()

    def _on_enter_ready(self):
        print("enter ready")
        message = self.get_cur_relation()
        self.message_q.append(
            TextSendMessage(message[:], emojis=hint_emoji)
        )
        message = "Choose an option!"
        self.message_q.append(TextSendMessage(message[:]))
        actions=[
            MessageTemplateAction(
                label='Add Relation',
                text='relation'
            )
        ]
        if(len(self.relations) > 0):
            actions.extend([
                MessageTemplateAction(
                    label='Delete Relation',
                    text='deletion'
                ),
                MessageTemplateAction(
                    label='Generate Graph',
                    text='generate'
                )
            ])

        self.message_q.append(
            TemplateSendMessage(
                alt_text="Choose an option",
                template=ButtonsTemplate(
                    title='Choose an option',
                    text="Choose what you want to do to the graph",
                    actions=actions
                )
            )
        )
        self.line_bot_reply()

    def _on_enter_delete(self):
        print("enter delete")
        message = self.get_cur_relation()
        self.message_q.append(TextSendMessage(message[:], emojis=hint_emoji))
        message = "Enter the number of relation you want to delete:"
        self.message_q.append(TextSendMessage(message[:]))
        self.line_bot_reply()

    def _on_enter_node1(self):
        print("enter node1")
        message = "Enter the second node:"
        self.message_q.append(TextSendMessage(message[:]))
        self.line_bot_reply()
    
    def _on_enter_node2(self):
        print("enter node2")
        self.message_q.append(
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
        self.line_bot_reply()

    def _on_enter_label(self):
        print("enter label")
        message = "Enter the label for relation:"
        self.message_q.append(TextSendMessage(message[:]))
        self.line_bot_reply()

    def _on_enter_other(self):
        print("enter other")
        self.message_q.append(
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
        self.line_bot_reply()


    def _on_enter_input(self):
        print("enter input")
        message = self.get_cur_relation()
        self.message_q.append(TextSendMessage(message[:], emojis=hint_emoji))

        message = "Enter the next node:"
        self.message_q.append(TextSendMessage(message[:]))

        message = \
            "$ You could also use these instructions to construct relations: \n" \
            "- node1 -> node2\n" \
            "- node3 -edge> node4"
        self.message_q.append(TextSendMessage(message[:], emojis=hint_emoji))

        self.line_bot_reply()



    def _on_enter_gen(self):
        print("enter gen")
        if self.graph_type == "directed":
            graph = Digraph()
        else:
            graph = Graph()
            
        graph.graph_attr["rankdir"] = self.graph_dir
        for relation in self.relations:
            print(relation)
            graph.node(relation[0], relation[0])
            graph.node(relation[1], relation[1])
            if (relation[2] != ""):
                graph.edge(relation[0], relation[1], relation[2])
            else: 
                graph.edge(relation[0], relation[1])
        graph.format = "png"
        graph.render(self.user_id, view=False, directory='dot-output')
        print("render successfully")

        im = pyimgur.Imgur(settings.IMGUR_CLIENT_ID)
        path = "dot-output/" + self.user_id + ".png"
        uploaded_image = im.upload_image(path)
        self.message_q.append(
            ImageSendMessage(
                original_content_url=uploaded_image.link,
                preview_image_url=uploaded_image.link
            )
        )

        self.message_q.append(
            TemplateSendMessage(
                alt_text="What's next?",
                template=ButtonsTemplate(
                    title='Next step',
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
        self.line_bot_reply()
