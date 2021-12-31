from django.conf import settings
from transitions.extensions import GraphMachine
from linebot import LineBotApi, WebhookParser
from linebot.models import  (
    TextSendMessage,
    TemplateSendMessage,
    ImageSendMessage,
    ButtonsTemplate,
    CarouselTemplate,
    CarouselColumn,
    MessageTemplateAction
) 

from graphviz import Graph, Digraph
import pyimgur

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
            "start",
            "dir",
            "shape",
            "ready",
            "delete",
            "input",
            "node1",
            "node2",
            "label",
            "other",
            "coloring",
            "color_input",
            "node_input",
            "gen",
            "wait"
        ]
        self.user_id = user_id

        self.machine = GraphMachine(
            model=self, 
            states=self.state,
            initial="start"
        )

        self.machine.add_transition("enter_type",     "start", "dir")
        self.machine.add_transition("unrecognized",   "start", "start")
        self.machine.add_transition("enter_dir",      "dir",   "shape")
        self.machine.add_transition("unrecognized",   "dir",   "dir")
        self.machine.add_transition("enter_shape",    "shape", "ready")
        self.machine.add_transition("unrecognized",   "shape", "shape")
        self.machine.add_transition("enter_input",    "ready", "input")
        self.machine.add_transition("enter_generate", "ready", "coloring")
        self.machine.add_transition("enter_del",      "ready", "delete")
        self.machine.add_transition("enter_restart",  "ready", "start")
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
        self.machine.add_transition("unrecognized",   "input", "input")
        self.machine.add_transition("enter_yes",      "coloring", "color_input")
        self.machine.add_transition("enter_no",       "coloring", "gen")
        self.machine.add_transition("unrecognized",   "coloring", "coloring")
        self.machine.add_transition("enter_color",    "color_input", "node_input")
        self.machine.add_transition("enter_ok",       "color_input", "gen")
        self.machine.add_transition("unrecognized",   "color_input", "color_input")
        self.machine.add_transition("enter_node",     "node_input", "color_input")
        self.machine.add_transition("unrecognized",   "node_input", "node_input")
        self.machine.add_transition("go_wait",        "gen", "wait")
        self.machine.add_transition("enter_continue", "wait", "ready")
        self.machine.add_transition("enter_get_link", "wait", "wait")
        self.machine.add_transition("enter_restart",  "wait", "start")
        self.machine.add_transition("unrecognized",   "wait", "wait")

        self.reply_token = ""
        self.graph_type = ""
        self.graph_dir = ""
        self.node_shape = ""
        self.cur_color = ""
        self.cur_relation = ["", "", ""]
        self.relations = []
        self.nodes = []
        self.message_q = []

    def line_bot_reply(self):
        line_bot_api.reply_message(
            self.reply_token,
            self.message_q
        )
        self.message_q = []

    def get_cur_relation(self):
        message = "📃 Current Input relations:"
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

    def get_cur_nodes(self):
        message = "📃 Node list:"
        count = 1
        for node in self.nodes:
            message += "\n" + str(count) + ".  " + node[0] + "  " 
            if (node[1] == "white"):
                message += "⚪"
            elif (node[1] == "cyan"):
                message += "🔵"
            elif (node[1] == "green"):
                message += "🟢"
            elif (node[1] == "yellow"):
                message += "🟡"
            count += 1
        return message


    def on_enter_start(self):
        print("enter start")
        self.message_q.append(
            TemplateSendMessage(
                alt_text="Choose graph type",
                template=CarouselTemplate(
                    columns=[
                        CarouselColumn(
                            thumbnail_image_url = 'https://i.imgur.com/1tjQxij.png',
                            title = "Directed graph",
                            text = "Graph with arrow edges",
                            actions = [
                                MessageTemplateAction(
                                    label = "Use Directed Graph",
                                    text = "directed"
                                )
                            ]
                        ),
                        CarouselColumn(
                            thumbnail_image_url = 'https://i.imgur.com/Kzuty7G.png',
                            title = "Undirected graph",
                            text = "Graph without arrow edges",
                            actions = [
                                MessageTemplateAction(
                                    label = "Use Undirected Graph",
                                    text = "undirected"
                                )
                            ]
                        )
                    ],
                    image_size= "contain"
                )
            )
        )
        self.line_bot_reply()

    def on_enter_dir(self):
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

    def on_enter_shape(self):
        print("enter shape")
        self.message_q.append(
            TemplateSendMessage(
                alt_text="Choose shape of node",
                template=ButtonsTemplate(
                    title='Shape',
                    text='Please choose the shape of nodes',
                    actions=[
                        MessageTemplateAction(
                            label='Ellipse',
                            text='ellipse'
                        ),
                        MessageTemplateAction(
                            label='Circle',
                            text='circle'
                        ),
                        MessageTemplateAction(
                            label='Rectangular',
                            text='box'
                        ),
                        MessageTemplateAction(
                            label='Plaintext',
                            text='plaintext'
                        )
                    ]
                )
            )
        )
        self.line_bot_reply()

    def on_enter_ready(self):
        print("enter ready")
        message = self.get_cur_relation()
        self.message_q.append(
            TextSendMessage(message[:])
        )
        message = "Choose an option!"
        self.message_q.append(TextSendMessage(message[:]))
        actions=[
            MessageTemplateAction(
                label='Add Relation',
                text='relation'
            ),
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
        actions.append(
            MessageTemplateAction(
                label='Restart',
                text='restart'
            )
        )
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

    def on_enter_delete(self):
        print("enter delete")
        message = self.get_cur_relation()
        self.message_q.append(TextSendMessage(message[:]))
        message = "Enter the number of relation you want to delete:"
        self.message_q.append(TextSendMessage(message[:]))
        self.line_bot_reply()

    def on_enter_node1(self):
        print("enter node1")
        message = "Enter the second node:"
        self.message_q.append(TextSendMessage(message[:]))
        self.line_bot_reply()
    
    def on_enter_node2(self):
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

    def on_enter_label(self):
        print("enter label")
        message = "Enter the label for relation:"
        self.message_q.append(TextSendMessage(message[:]))
        self.line_bot_reply()

    def on_enter_other(self):
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


    def on_enter_input(self):
        print("enter input")
        message = self.get_cur_relation()
        self.message_q.append(TextSendMessage(message[:]))

        message = "Enter the next node:"
        self.message_q.append(TextSendMessage(message[:]))

        message = \
            "$ You could also use these instructions to construct relations: \n" \
            "- node1 -> node2\n" \
            "- node3 -edge> node4"
        self.message_q.append(TextSendMessage(message[:], emojis=hint_emoji))

        self.line_bot_reply()

    
    def on_enter_coloring(self):
        print("enter coloring")
        for relation in self.relations:
            if (not relation[0] in [item[0] for item in self.nodes]):
                self.nodes.append([relation[0], "white"])
            if (not relation[1] in [item[0] for item in self.nodes]):
                self.nodes.append([relation[1], "white"])

        self.message_q.append(
            TemplateSendMessage(
                alt_text="Do you want to color the nodes?",
                template=ButtonsTemplate(
                    title='Color node',
                    text="Do you want to color the nodes?",
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

    def on_enter_color_input(self):
        print("enter color input")

        message = self.get_cur_nodes()
        self.message_q.append(
            TextSendMessage(text=message[:])
        )

        self.message_q.append(
            TemplateSendMessage(
                alt_text="Enter color",
                template=ButtonsTemplate(
                    title='Pick a color',
                    text="Pick a color from below or finish coloring",
                    actions=[
                        MessageTemplateAction(
                            label='🟡 Yellow',
                            text='yellow'
                        ),
                        MessageTemplateAction(
                            label='🟢 Green',
                            text='green'
                        ),
                        MessageTemplateAction(
                            label='🔵 Cyan',
                            text='cyan'
                        ),
                        MessageTemplateAction(
                            label='Done',
                            text='done'
                        ),
                    ]
                )
            )
        )
        self.line_bot_reply()

    def on_enter_node_input(self):
        print("enter node input")

        message = self.get_cur_nodes()
        self.message_q.append(
            TextSendMessage(text=message[:])
        )

        message = "Please enter node number from the above list.\nYou could seperate"\
                "different nodes with spaces"
        self.message_q.append(
            TextSendMessage(text=message)
        )
        self.line_bot_reply()


    def on_enter_gen(self):
        print("enter gen")
        if self.graph_type == "directed":
            graph = Digraph()
        else:
            graph = Graph()
            
        graph.graph_attr["rankdir"] = self.graph_dir
        for node in self.nodes:
            graph.node(node[0], node[0], style='filled', fillcolor=node[1], shape=self.node_shape)
        for relation in self.relations:
            print(relation)
            if (relation[2] != ""):
                graph.edge(relation[0], relation[1], relation[2])
            else: 
                graph.edge(relation[0], relation[1])
        graph.format = "png"
        graph.render(self.user_id, view=False, directory='dot-output')
        print("render successfully")

        path = "dot-output/" + self.user_id + ".png"
        im = pyimgur.Imgur(settings.IMGUR_CLIENT_ID)
        uploaded_image = im.upload_image(path)
        self.upload_link = uploaded_image.link
        self.message_q.append(
            ImageSendMessage(
                original_content_url=uploaded_image.link,
                preview_image_url=uploaded_image.link
            )
        )
        self.go_wait()

    def on_enter_wait(self):
        print("enter wait")
        self.message_q.append(
            TemplateSendMessage(
                alt_text="What's next?",
                template=ButtonsTemplate(
                    title='Next step',
                    text="What's next?",
                    actions=[
                        MessageTemplateAction(
                            label='Get image link',
                            text='get link'
                        ),
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
