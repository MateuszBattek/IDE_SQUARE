from PyQt5 import QtCore, QtGui, QtWidgets
from pyqtgraph import GraphicsLayoutWidget

def mainStyleSheet():
    return """
* {
    color: black;
}

QWidget#central_widget {
    background: qlineargradient(y1:0, y2:1, stop:0.1 #d4e1bd, stop:0.7 #f4f9e1, stop:1 #ffffff);
}


QPushButton {
    padding: 5px;
    border-radius: 5px;
    background-color: #b2d6a1;
    border: 1px solid gray;
}

QPushButton:hover {
    background-color: #9dbd8e;
}


QLineEdit {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px;
}

QTextEdit {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px;
}

QTextEdit:focus {
    border: 2px solid #4a90e2;
}

QComboBox {
    background-color: white;
    border: 1px solid gray;
}

GraphicsLayoutWidget#graph {
    border: 1px solid black;
}


QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #888;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    width: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}



QPushButton#tree_button, #ai_button {
    background-color: #e0f4d4;
    font-weight: bold;
}
QPushButton#tree_button:hover, #ai_button:hover {
    background-color: #d6ebca;
}

QPushButton#bot_button {
    background-color: #c8e8f4;
    font-weight: bold;
}
QPushButton#bot_button:hover {
    background-color: #b4d8e8;
}


QPushButton#sm_button, #solver_button {
    background-color: #cfedc0;
    font-weight: bold;
}
QPushButton#sm_button:hover, #solver_button:hover {
    background-color: #c0dbb2;
}


QPushButton#square_button, #assertions_button, #gen_button {
    background-color: #b2d6a1;
    font-weight: bold;
}
QPushButton#square_button:hover, #assertions_button:hover, #gen_button:hover {
    background-color: #9dbd8e;
}


QPushButton#expand_button, #reset_button {
    background-color: #a1c8a1;
    font-weight: bold;
}
QPushButton#expand_button:hover, #reset_button:hover, #class_button:hover, #trans_button:hover {
    background-color: #91b591;
}



QPushButton#class_button, #trans_button {
    background-color: #a1c8a1;
}
"""

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setMinimumSize(1200, 800)
        MainWindow.resize(1200, 800)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("central_widget")

        # Main layout for the central widget
        self.main_v_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.main_v_layout.setContentsMargins(20, 20, 20, 20)
        self.main_v_layout.setSpacing(20)

        font = QtGui.QFont("MS Shell Dlg 2", 9)
        MainWindow.setFont(font)

        font_16 = QtGui.QFont("MS Shell Dlg 2", 16)
        font_16.setBold(True)
        font_14 = QtGui.QFont("MS Shell Dlg 2", 14)
        font_14.setBold(True)
        font_12 = QtGui.QFont("MS Shell Dlg 2", 12)
        font_10 = QtGui.QFont("MS Shell Dlg 2", 10)

        MainWindow.setStyleSheet(mainStyleSheet())

        # menu buttons
        self.buttonwidget = QtWidgets.QWidget(self.centralwidget)
        self.buttonwidget.setObjectName("buttons")
        self.button_h_layout = QtWidgets.QHBoxLayout(self.buttonwidget)
        self.button_h_layout.setContentsMargins(0, 0, 0, 0)
        self.button_h_layout.setSpacing(10)
        self.main_v_layout.addWidget(self.buttonwidget)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.square_button = QtWidgets.QPushButton(self.buttonwidget)
        self.square_button.setSizePolicy(sizePolicy)
        self.square_button.setObjectName("square_button")
        self.square_button.setText("Add Square")
        self.button_h_layout.addWidget(self.square_button)

        self.tree_button = QtWidgets.QPushButton(self.buttonwidget)
        self.tree_button.setSizePolicy(sizePolicy)
        self.tree_button.setObjectName("tree_button")
        self.tree_button.setText("State Tree")
        self.tree_button.setVisible(False)
        self.button_h_layout.addWidget(self.tree_button)

        self.sm_button = QtWidgets.QPushButton(self.buttonwidget)
        self.sm_button.setSizePolicy(sizePolicy)
        self.sm_button.setObjectName("sm_button")
        self.sm_button.setText("State Machine")
        self.sm_button.setVisible(False)
        self.button_h_layout.addWidget(self.sm_button)

        self.assertions_button = QtWidgets.QPushButton(self.buttonwidget)
        self.assertions_button.setSizePolicy(sizePolicy)
        self.assertions_button.setObjectName("assertions_button")
        self.assertions_button.setText("Assertions")
        self.assertions_button.setVisible(False)
        self.button_h_layout.addWidget(self.assertions_button)

        self.expand_button = QtWidgets.QPushButton(self.buttonwidget)
        self.expand_button.setSizePolicy(sizePolicy)
        self.expand_button.setObjectName("expand_button")
        self.expand_button.setText("Expand State")
        self.expand_button.setVisible(False)
        self.button_h_layout.addWidget(self.expand_button)

        self.ai_button = QtWidgets.QPushButton(self.buttonwidget)
        self.ai_button.setSizePolicy(sizePolicy)
        self.ai_button.setObjectName("ai_button")
        self.ai_button.setText("LLM Chat")
        self.button_h_layout.addWidget(self.ai_button)

        self.bot_button = QtWidgets.QPushButton(self.buttonwidget)
        self.bot_button.setSizePolicy(sizePolicy)
        self.bot_button.setObjectName("bot_button")
        self.bot_button.setText("Bot")
        self.button_h_layout.addWidget(self.bot_button)

        self.solver_button = QtWidgets.QPushButton(self.buttonwidget)
        self.solver_button.setSizePolicy(sizePolicy)
        self.solver_button.setObjectName("solver_button")
        self.solver_button.setText("Solver")
        self.button_h_layout.addWidget(self.solver_button)

        self.gen_button = QtWidgets.QPushButton(self.buttonwidget)
        self.gen_button.setSizePolicy(sizePolicy)
        self.gen_button.setObjectName("gen_button")
        self.gen_button.setText("Generate Code")
        self.gen_button.setVisible(False)
        self.button_h_layout.addWidget(self.gen_button)

        self.save_button = QtWidgets.QPushButton(self.buttonwidget)
        self.save_button.setSizePolicy(sizePolicy)
        self.save_button.setObjectName("save_button")
        self.save_button.setText("Save project")
        self.save_button.setVisible(False)
        self.button_h_layout.addWidget(self.save_button)

        self.load_button = QtWidgets.QPushButton(self.buttonwidget)
        self.load_button.setSizePolicy(sizePolicy)
        self.load_button.setObjectName("load_button")
        self.load_button.setText("Load project")
        self.button_h_layout.addWidget(self.load_button)

        self.reset_button = QtWidgets.QPushButton(self.buttonwidget)
        self.reset_button.setSizePolicy(sizePolicy)
        self.reset_button.setObjectName("reset_button")
        self.reset_button.setText("Reset")
        self.button_h_layout.addWidget(self.reset_button)

        self.log_button = QtWidgets.QPushButton(self.buttonwidget)
        self.log_button.setSizePolicy(sizePolicy)
        self.log_button.setObjectName("log_button")
        self.log_button.setText("Show Logs")
        self.button_h_layout.addWidget(self.log_button)

        # main area
        self.main_widget = QtWidgets.QWidget(self.centralwidget)
        self.main_v_layout.addWidget(self.main_widget)
        self.main_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # Use a layout for main_widget to manage its sub-pages
        self.main_content_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.main_content_layout.setContentsMargins(0, 0, 0, 0)

        # add square widget
        self.square = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.square)

        # add square widget layout
        self.square_v_layout = QtWidgets.QVBoxLayout(self.square)
        self.square_v_layout.setContentsMargins(50, 20, 50, 20)
        self.square_v_layout.setSpacing(10)

        self.addsquare = QtWidgets.QLabel(self.square)
        self.addsquare.setFont(font_16)
        self.addsquare.setAlignment(QtCore.Qt.AlignCenter)
        self.addsquare.setText("Add First Logical Square")
        self.square_v_layout.addWidget(self.addsquare)

        self.addlabel = QtWidgets.QLabel(self.square)
        self.addlabel.setFont(font_12)
        self.addlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.addlabel.setWordWrap(True)
        self.addlabel.setText("Add chosen corners to create first states. "
                         "If you leave any vertex empty it will be assigned the \'true\' value.")
        self.square_v_layout.addWidget(self.addlabel)

        self.expandbox = QtWidgets.QComboBox(self.square)
        self.expandbox.setMinimumSize(111, 31)
        self.expandbox.setVisible(False)
        self.square_v_layout.addWidget(self.expandbox, 0, QtCore.Qt.AlignCenter)

        # Grid for inputs
        self.square_grid = QtWidgets.QGridLayout()
        self.square_grid.setSpacing(20)
        
        self.labelA = QtWidgets.QLabel("A", self.square)
        self.labelA.setFont(font_14)
        self.labelA.setAlignment(QtCore.Qt.AlignCenter)
        self.inputA = QtWidgets.QLineEdit(self.square)
        self.inputA.setMinimumHeight(31)
        self.square_grid.addWidget(self.labelA, 0, 0)
        self.square_grid.addWidget(self.inputA, 0, 1)

        self.labelE = QtWidgets.QLabel("E", self.square)
        self.labelE.setFont(font_14)
        self.labelE.setAlignment(QtCore.Qt.AlignCenter)
        self.inputE = QtWidgets.QLineEdit(self.square)
        self.inputE.setMinimumHeight(31)
        self.square_grid.addWidget(self.labelE, 1, 0)
        self.square_grid.addWidget(self.inputE, 1, 1)

        self.labelI = QtWidgets.QLabel("I", self.square)
        self.labelI.setFont(font_14)
        self.labelI.setAlignment(QtCore.Qt.AlignCenter)
        self.inputI = QtWidgets.QLineEdit(self.square)
        self.inputI.setMinimumHeight(31)
        self.square_grid.addWidget(self.labelI, 2, 0)
        self.square_grid.addWidget(self.inputI, 2, 1)

        self.labelO = QtWidgets.QLabel("O", self.square)
        self.labelO.setFont(font_14)
        self.labelO.setAlignment(QtCore.Qt.AlignCenter)
        self.inputO = QtWidgets.QLineEdit(self.square)
        self.inputO.setMinimumHeight(31)
        self.square_grid.addWidget(self.labelO, 3, 0)
        self.square_grid.addWidget(self.inputO, 3, 1)

        self.square_v_layout.addLayout(self.square_grid)

        self.add_square_button = QtWidgets.QPushButton(self.square)
        self.add_square_button.setMinimumSize(171, 41)
        self.add_square_button.setFont(font)
        self.add_square_button.setText("Add")
        self.square_v_layout.addWidget(self.add_square_button, 0, QtCore.Qt.AlignCenter)
        self.square_v_layout.addStretch()

        # state tree widget
        self.tree = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.tree)
        self.tree.setVisible(False)

        # state tree widget layout
        self.tree_v_layout = QtWidgets.QVBoxLayout(self.tree)
        self.tree_v_layout.setContentsMargins(20, 20, 20, 20)
        self.tree_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.tree)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("State Tree")
        self.tree_v_layout.addWidget(widget_title)

        self.statetree = GraphicsLayoutWidget(self.tree)
        self.statetree.setBackground('w')
        self.statetree.setObjectName("graph")
        self.tree_plot = self.statetree.addPlot()
        self.tree_plot.hideAxis('left')
        self.tree_plot.hideAxis('bottom')
        self.tree_v_layout.addWidget(self.statetree)

        self.name_button = QtWidgets.QPushButton(self.tree)
        self.name_button.setMinimumSize(171, 41)
        self.name_button.setFont(font)
        self.name_button.setText("Set Names")
        self.tree_v_layout.addWidget(self.name_button, 0, QtCore.Qt.AlignCenter)

        # set name widget
        self.names = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.names)
        self.names.setVisible(False)

        # set name widget layout
        self.names_v_layout = QtWidgets.QVBoxLayout(self.names)
        self.names_v_layout.setContentsMargins(50, 20, 50, 20)
        self.names_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.names)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("Set Names For States")
        self.names_v_layout.addWidget(widget_title)

        addlabel = QtWidgets.QLabel(self.names)
        addlabel.setFont(font_12)
        addlabel.setAlignment(QtCore.Qt.AlignCenter)
        addlabel.setWordWrap(True)
        addlabel.setText("Here you can choose your state names. Select a state "
                         "from box below and input new name in the line edit.")
        self.names_v_layout.addWidget(addlabel)

        self.namebox = QtWidgets.QComboBox(self.names)
        self.namebox.setMinimumSize(111, 31)
        self.names_v_layout.addWidget(self.namebox, 0, QtCore.Qt.AlignCenter)
        
        self.assertlabel = QtWidgets.QLabel(self.names)
        self.assertlabel.setFont(font)
        self.assertlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.assertlabel.setText("State Assertion: ")
        self.names_v_layout.addWidget(self.assertlabel)

        self.currentNameLabel = QtWidgets.QLabel(self.names)
        self.currentNameLabel.setFont(font)
        self.currentNameLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.currentNameLabel.setText("No name assigned")
        self.names_v_layout.addWidget(self.currentNameLabel)

        self.name_input = QtWidgets.QLineEdit(self.names)
        self.name_input.setMinimumHeight(31)
        self.name_input.setFont(font)
        self.names_v_layout.addWidget(self.name_input)

        self.change_name_button = QtWidgets.QPushButton(self.names)
        self.change_name_button.setMinimumSize(171, 41)
        self.change_name_button.setFont(font)
        self.change_name_button.setText("Change Name")
        self.names_v_layout.addWidget(self.change_name_button, 0, QtCore.Qt.AlignCenter)
        self.names_v_layout.addStretch()

        # state machine code widget
        self.code = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.code)
        self.code.setVisible(False)

        # state machine code widget layout
        self.code_v_layout = QtWidgets.QVBoxLayout(self.code)
        self.code_v_layout.setContentsMargins(20, 20, 20, 20)
        self.code_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.code)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("Generate State Machine Code")
        self.code_v_layout.addWidget(widget_title)

        self.smcode = QtWidgets.QTextEdit(self.code)
        self.smcode.setReadOnly(True)
        self.smcode.setFont(font_10)
        self.code_v_layout.addWidget(self.smcode)

        # code generation buttons
        self.generate_buttons = QtWidgets.QWidget(self.code)
        buttons = QtWidgets.QHBoxLayout(self.generate_buttons)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(40)
        self.code_v_layout.addWidget(self.generate_buttons)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.class_button = QtWidgets.QPushButton(self.generate_buttons)
        self.class_button.setSizePolicy(sizePolicy)
        self.class_button.setText("Class Code")
        self.class_button.setObjectName("class_button")
        buttons.addWidget(self.class_button)

        self.qt_button = QtWidgets.QPushButton(self.generate_buttons)
        self.qt_button.setSizePolicy(sizePolicy)
        self.qt_button.setObjectName("qt_button")
        self.qt_button.setText("Qt Code")
        buttons.addWidget(self.qt_button)

        self.trans_button = QtWidgets.QPushButton(self.generate_buttons)
        self.trans_button.setSizePolicy(sizePolicy)
        self.trans_button.setObjectName("trans_button")
        self.trans_button.setText("Transition Code")
        buttons.addWidget(self.trans_button)

        # self.sml_button = QtWidgets.QPushButton(self.generate_buttons)
        # self.sml_button.setSizePolicy(sizePolicy)
        # self.sml_button.setObjectName("sml_button")
        # self.sml_button.setText("SML Code")
        # buttons.addWidget(self.sml_button)

        # sm graph and transitions widget
        self.transitions = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.transitions)
        self.transitions.setVisible(False)

        # sm graph and transitions widget layout
        self.trans_v_layout = QtWidgets.QVBoxLayout(self.transitions)
        self.trans_v_layout.setContentsMargins(20, 20, 20, 20)
        self.trans_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.transitions)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("State Machine Diagram")
        self.trans_v_layout.addWidget(widget_title)

        # Horizontal layout for graph and theorem prover
        self.trans_h_layout = QtWidgets.QHBoxLayout()
        self.trans_v_layout.addLayout(self.trans_h_layout)

        # Left side: Graph and transition inputs
        self.graph_side = QtWidgets.QWidget()
        self.graph_v_layout = QtWidgets.QVBoxLayout(self.graph_side)
        self.trans_h_layout.addWidget(self.graph_side, 3)

        self.sm_graph = GraphicsLayoutWidget(self.graph_side)
        self.sm_graph.setObjectName("graph")
        self.sm_graph.setBackground('w')
        self.sm_plot = self.sm_graph.addPlot()
        self.sm_plot.hideAxis('left')
        self.sm_plot.hideAxis('bottom')
        self.graph_v_layout.addWidget(self.sm_graph)

        self.translabel = QtWidgets.QLabel(self.graph_side)
        self.translabel.setFont(font_12)
        self.translabel.setAlignment(QtCore.Qt.AlignCenter)
        self.translabel.setWordWrap(True)
        self.translabel.setText("Here you can add transitions between states. "
                           "Select suitable states from boxes, put transition "
                           "condition in the input line and click ENTER.")
        self.graph_v_layout.addWidget(self.translabel)

        # Transition inputs bar
        self.trans_input_bar = QtWidgets.QHBoxLayout()
        self.graph_v_layout.addLayout(self.trans_input_bar)

        fromlabel = QtWidgets.QLabel("FROM", self.graph_side)
        fromlabel.setFont(font)
        self.frombox = QtWidgets.QComboBox(self.graph_side)
        self.frombox.setMinimumWidth(100)
        self.trans_input_bar.addWidget(fromlabel)
        self.trans_input_bar.addWidget(self.frombox)

        tolabel = QtWidgets.QLabel("TO", self.graph_side)
        tolabel.setFont(font)
        self.tobox = QtWidgets.QComboBox(self.graph_side)
        self.tobox.setMinimumWidth(100)
        self.trans_input_bar.addWidget(tolabel)
        self.trans_input_bar.addWidget(self.tobox)

        iflabel = QtWidgets.QLabel("IF", self.graph_side)
        iflabel.setFont(font)
        self.ifinput = QtWidgets.QLineEdit(self.graph_side)
        self.ifinput.setFont(font)
        self.trans_input_bar.addWidget(iflabel)
        self.trans_input_bar.addWidget(self.ifinput)

        # Right side: Theorem prover
        self.prover_side = QtWidgets.QWidget()
        self.prover_v_layout = QtWidgets.QVBoxLayout(self.prover_side)
        self.prover_side.setFixedWidth(300)
        self.trans_h_layout.addWidget(self.prover_side)

        self.theorem_prover_button = QtWidgets.QPushButton("Analyze states reachability", self.prover_side)
        self.prover_v_layout.addWidget(self.theorem_prover_button)

        sm_prover_label = QtWidgets.QLabel(self.prover_side)
        sm_prover_label.setFont(font_10)
        sm_prover_label.setWordWrap(True)
        sm_prover_label.setText("Built-in Z3 theorem prover will analyze state"
                                " machine to see if there are state pairs (a, b),"
                                " where state a is not reachable from state b")
        self.prover_v_layout.addWidget(sm_prover_label)

        self.theorem_prover_feedback = QtWidgets.QTextEdit(self.prover_side)
        self.theorem_prover_feedback.setReadOnly(True)
        self.theorem_prover_feedback.setFont(font_10)
        self.prover_v_layout.addWidget(self.theorem_prover_feedback)

        # assertions widget
        self.assertions = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.assertions)
        self.assertions.setVisible(False)

        # assertions widget layout
        self.assert_v_layout = QtWidgets.QVBoxLayout(self.assertions)
        self.assert_v_layout.setContentsMargins(20, 20, 20, 20)
        self.assert_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.assertions)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("State Assertions")
        self.assert_v_layout.addWidget(widget_title)

        self.assert_tree = QtWidgets.QTextEdit(self.assertions)
        self.assert_tree.setStyleSheet("color: gray;")
        self.assert_tree.setReadOnly(True)
        self.assert_tree.setFont(font_10)
        self.assert_v_layout.addWidget(self.assert_tree)

        # solver widget
        self.solver = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.solver)
        self.solver.setVisible(False)

        # solver widget layout
        self.solver_v_layout = QtWidgets.QVBoxLayout(self.solver)
        self.solver_v_layout.setContentsMargins(20, 20, 20, 20)
        self.solver_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.solver)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("Logical Disjointness Verification")
        self.solver_v_layout.addWidget(widget_title)

        self.solver_input = QtWidgets.QTextEdit(self.solver)
        self.solver_input.setStyleSheet("color: gray;")
        self.solver_input.setFont(font_10)
        self.solver_v_layout.addWidget(self.solver_input)

        self.solver_feedback = QtWidgets.QTextEdit(self.solver)
        self.solver_feedback.setReadOnly(True)
        self.solver_feedback.setStyleSheet("color: gray;")
        self.solver_feedback.setFont(font_10)
        self.solver_v_layout.addWidget(self.solver_feedback)

        solverlabel = QtWidgets.QLabel(self.solver)
        solverlabel.setFont(font_12)
        solverlabel.setAlignment(QtCore.Qt.AlignCenter)
        solverlabel.setWordWrap(True)
        solverlabel.setText("Here you can check whether all pairs of given "
                            "states are logically disjoint, meaning that "
                            "no two states share a common truth assignment.")
        self.solver_v_layout.addWidget(solverlabel)

        self.check_states_button = QtWidgets.QPushButton(self.solver)
        self.check_states_button.setMinimumSize(171, 41)
        self.check_states_button.setFont(font)
        self.check_states_button.setObjectName("check_states_button")
        self.check_states_button.setText("Check States")
        self.solver_v_layout.addWidget(self.check_states_button, 0, QtCore.Qt.AlignCenter)


        self.logs = QtWidgets.QWidget(self.main_widget)
        self.logs.setObjectName("logs")
        self.main_content_layout.addWidget(self.logs)

        self.log_v_layout = QtWidgets.QVBoxLayout(self.logs)
        self.log_output = QtWidgets.QTextEdit(self.logs)
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("log_output")
        self.log_v_layout.addWidget(self.log_output)

        self.logs.setVisible(False)  # Keep it hidden by default


        # ai widget
        self.ai = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.ai)
        self.ai.setVisible(False)

        self.ai_v_layout = QtWidgets.QVBoxLayout(self.ai)
        self.ai_v_layout.setContentsMargins(50, 20, 50, 20)
        self.ai_v_layout.setSpacing(10)

        widget_title = QtWidgets.QLabel(self.ai)
        widget_title.setFont(font_16)
        widget_title.setAlignment(QtCore.Qt.AlignCenter)
        widget_title.setText("LLM Chat")
        self.ai_v_layout.addWidget(widget_title)

        self.ai.ai_feedback = QtWidgets.QTextEdit(self.ai)
        self.ai.ai_feedback.setReadOnly(True)
        self.ai.ai_feedback.setFont(font_10)
        self.ai.ai_feedback.setStyleSheet("background-color: #ffffff; color: #000000; border: 1px solid #d0d0d0; border-radius: 4px; padding: 4px;")
        self.ai_v_layout.addWidget(self.ai.ai_feedback)

        ailabel_info = QtWidgets.QLabel(self.ai)
        ailabel_info.setFont(font_12)
        ailabel_info.setAlignment(QtCore.Qt.AlignCenter)
        ailabel_info.setWordWrap(True)
        ailabel_info.setText("Here you can ask LLM to help you complete logical squares. "
                        "Give it a domain name and selected square corners and it will try "
                        "to generate remaining vertices.")
        self.ai_v_layout.addWidget(ailabel_info)

        self.ai.ai_input = QtWidgets.QTextEdit(self.ai)
        self.ai.ai_input.setMaximumHeight(100)
        self.ai.ai_input.setFont(font_10)
        self.ai.ai_input.setStyleSheet("background-color: #ffffff; color: #000000; border: 1px solid #d0d0d0; border-radius: 4px; padding: 4px;")
        self.ai_v_layout.addWidget(self.ai.ai_input)

        ailabel_ex = QtWidgets.QLabel(self.ai)
        ailabel_ex.setFont(font_12)
        ailabel_ex.setAlignment(QtCore.Qt.AlignCenter)
        ailabel_ex.setWordWrap(True)
        ailabel_ex.setText("Example input can look like this:\n"
                        "Airport traffic management system, A=taxiing")
        self.ai_v_layout.addWidget(ailabel_ex)

        self.send_request_button = QtWidgets.QPushButton(self.ai)
        self.send_request_button.setMinimumSize(171, 41)
        self.send_request_button.setFont(font)
        self.send_request_button.setText("Send Request")
        self.ai_v_layout.addWidget(self.send_request_button, 0, QtCore.Qt.AlignCenter)

        # bot widget
        self.bot = QtWidgets.QWidget(self.main_widget)
        self.main_content_layout.addWidget(self.bot)
        self.bot.setVisible(False)

        self.bot_v_layout = QtWidgets.QVBoxLayout(self.bot)
        self.bot_v_layout.setContentsMargins(30, 20, 30, 20)
        self.bot_v_layout.setSpacing(10)

        bot_title = QtWidgets.QLabel(self.bot)
        bot_title.setFont(font_16)
        bot_title.setAlignment(QtCore.Qt.AlignCenter)
        bot_title.setText("IDE Bot")
        self.bot_v_layout.addWidget(bot_title)

        bot_subtitle = QtWidgets.QLabel(self.bot)
        bot_subtitle.setFont(font_12)
        bot_subtitle.setAlignment(QtCore.Qt.AlignCenter)
        bot_subtitle.setWordWrap(True)
        # bot_subtitle.setText(
        #     "Ask me to perform any IDE operation using natural language."
        # )
        self.bot_v_layout.addWidget(bot_subtitle)

        self.bot.chat_log = QtWidgets.QTextEdit(self.bot)
        self.bot.chat_log.setReadOnly(True)
        self.bot.chat_log.setFont(font_10)
        self.bot.chat_log.setStyleSheet(
            "background-color: #f7fbf7; color: #000000;"
            " border: 1px solid #c8dfc8; border-radius: 6px; padding: 6px;"
        )
        self.bot_v_layout.addWidget(self.bot.chat_log)

        # input row
        self.bot_input_row = QtWidgets.QHBoxLayout()
        self.bot_input_row.setSpacing(10)
        self.bot_v_layout.addLayout(self.bot_input_row)

        self.bot.prompt_input = QtWidgets.QTextEdit(self.bot)
        self.bot.prompt_input.setMaximumHeight(80)
        self.bot.prompt_input.setFont(font_10)
        self.bot.prompt_input.setPlaceholderText("Type a command…")
        self.bot.prompt_input.setStyleSheet(
            "background-color: #ffffff; color: #000000;"
            " border: 1px solid #c8dfc8; border-radius: 6px; padding: 6px;"
        )
        self.bot_input_row.addWidget(self.bot.prompt_input)

        self.bot.send_button = QtWidgets.QPushButton("Send", self.bot)
        self.bot.send_button.setMinimumSize(80, 80)
        self.bot.send_button.setFont(font)
        self.bot.send_button.setObjectName("bot_send_button")
        self.bot_input_row.addWidget(self.bot.send_button)

        bot_hint = QtWidgets.QLabel("Ctrl+Enter to send", self.bot)
        bot_hint.setFont(font)
        bot_hint.setAlignment(QtCore.Qt.AlignRight)
        bot_hint.setStyleSheet("color: #999999;")
        self.bot_v_layout.addWidget(bot_hint)
        # ─────────────────────────────────────────────────────────────────────

        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtCore.QCoreApplication.translate("MainWindow", "State Machine Generator"))
        self.log_button.setText("Show Logs")



