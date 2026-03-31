from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget

from views.gui import Ui_MainWindow
from components.fsm_components.fsm import LogicalSquareFSM
from components.fsm_components.sm_analyzer import find_unreachable_pairs_in_state_machine
from components.fsm_components import graph_gen as gg
from components import ai_module as aim
from components import solver
from components.file_storage import FileStorage
from components.logger import LogManager
from PyQt5 import QtGui


class MainWindowController(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.file_storage = FileStorage()
        self.fsm = LogicalSquareFSM()

        self.parent_id = self.fsm.root
        self.expanded_states = []
        self.class_code = None
        self.transition_code = None
        self.qt_code = None
        self.sml_code = None
        self.expanded = False
        self.logger = LogManager()
        self.agent_client = aim.AgentServiceClient()

        self.ui.inputA.returnPressed.connect(lambda: self.move_focus(self.ui.inputE))
        self.ui.inputE.returnPressed.connect(lambda: self.move_focus(self.ui.inputI))
        self.ui.inputI.returnPressed.connect(lambda: self.move_focus(self.ui.inputO))
        self.ui.inputO.returnPressed.connect(self.add_square)

        self.ui.add_square_button.clicked.connect(self.add_square)
        self.ui.name_button.clicked.connect(self.show_name_widget)
        self.ui.namebox.currentTextChanged.connect(self.update_assertion)
        self.ui.change_name_button.clicked.connect(self.add_name)
        self.ui.send_request_button.clicked.connect(self.sent_request)
        self.ui.check_states_button.clicked.connect(self.check_states)

        self.ui.ifinput.returnPressed.connect(self.add_transition)
        self.ui.frombox.currentIndexChanged.connect(self.update_state_box)

        self.ui.square_button.clicked.connect(self.show_square_widget)
        self.ui.tree_button.clicked.connect(self.show_tree_widget)
        self.ui.sm_button.clicked.connect(self.show_sm_widget)
        self.ui.assertions_button.clicked.connect(self.show_assertions_widget)
        self.ui.expand_button.clicked.connect(self.show_square_widget)
        self.ui.save_button.clicked.connect(self.save_project)
        self.ui.load_button.clicked.connect(self.load_project)
        self.ui.log_button.clicked.connect(self.show_logs)

        self.ui.ai_button.clicked.connect(self.show_ai_widget)
        self.ui.solver_button.clicked.connect(self.show_solver_widget)
        self.ui.gen_button.clicked.connect(self.show_code_widget)

        self.ui.theorem_prover_button.clicked.connect(self.analyze_sm_states_reachability)

        self.gen_buttons = [self.ui.class_button, self.ui.trans_button, self.ui.qt_button,
                            # self.ui.sml_button
                            ]
        for button in self.gen_buttons:
            button.clicked.connect(self.show_sm_code)

        self.ui.reset_button.clicked.connect(self.reset_action)

    def show_logs(self):
        self.hide_widgets(self.ui.logs)
        log_entries = self.logger.get_logs()
        self.ui.log_output.setPlainText('\n'.join(log_entries))

    def save_project(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if not file_path:
            QMessageBox.warning(self, "Warning", "No file path selected. Project not saved.")
            return
        try:
            if isinstance(file_path, str) and file_path.strip():
                fsm_state = self.fsm.serialize_object()
                solver_example = [line.strip() for line in self.ui.solver_input.toPlainText().splitlines() if
                                  line.strip()]
                self.file_storage.save_state(file_path, fsm_state, solver_example)
                self.logger.log("Saved project to file.")  # Log the action
                QMessageBox.information(self, "Success", "Project saved successfully.")
            else:
                QMessageBox.critical(self, "Error", "Invalid file path provided for saving.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

    def load_project(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project File", "", "JSON Files (*.json);;All Files (*)")
        if not file_path:
            QMessageBox.warning(self, "Warning", "No file path selected. Project not loaded.")
            return
        try:
            fsm_state, solver_example = self.file_storage.load_state(file_path)
            self.logger.log("Loaded project from file.")
            self.fsm = LogicalSquareFSM.deserialize_logical_square_fsm(fsm_state)
            self.expanded_states = [key for key, value in self.fsm.span_tree.items() if len(value['children']) != 0]
            if solver_example:
                self.ui.solver_input.setPlainText("\n".join(solver_example))
            if len(self.fsm.latest_states) > 0:
                for input_field in [self.ui.inputA, self.ui.inputE, self.ui.inputI, self.ui.inputO]:
                    input_field.clear()
                self.show_tree_widget()
                self.show_missing_buttons()
            QMessageBox.information(self, "Success", "Project loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

    def move_focus(self, next_widget):
        next_widget.setFocus()

    def hide_widgets(self, active_widget):
        for widget in self.ui.main_widget.children():
            if isinstance(widget, QWidget) and widget != active_widget:
                widget.setVisible(False)
        active_widget.setVisible(True)

    def show_tree_widget(self):
        self.hide_widgets(self.ui.tree)
        self.display_tree_graph()

    def show_name_widget(self):
        self.hide_widgets(self.ui.names)
        all_state_ids = [state_id for state_id in self.fsm.span_tree.keys()
                         if state_id not in self.expanded_states]
        self.fill_states_box(all_state_ids, self.ui.namebox)

    def update_assertion(self):
        state_id = self.ui.namebox.currentText()
        try:
            node = self.fsm.span_tree[state_id]
            state = node["state"]
            assertion = state.assert_state()
            current_name = state.name if state.name else "No name assigned"
            self.ui.currentNameLabel.setText(f"State Name: {current_name}")
            self.ui.assertlabel.setText(f"State Assertion: {assertion}")
        except KeyError:
            pass

    def show_sm_widget(self):
        self.hide_widgets(self.ui.transitions)
        self.ui.frombox.clear()
        for state_id in self.fsm.span_tree.keys():
            if state_id not in self.expanded_states:
                self.ui.frombox.addItem(str(state_id))
        all_states = [(state_key, state_data) for state_key, state_data in self.fsm.span_tree.items()
                      if state_key not in self.expanded_states]

        transitions = []
        for t in self.fsm.transitions:
            if isinstance(t, (list, tuple)) and len(t) == 3:
                transitions.append((t[0], t[1], t[2]))
        gg.draw_state_machine(self.ui.sm_plot, transitions, all_states)

    def show_assertions_widget(self):
        self.hide_widgets(self.ui.assertions)
        tree_str = self.fsm.display_tree()
        self.ui.assert_tree.clear()
        self.ui.assert_tree.append(tree_str)

    def show_square_widget(self):
        self.fill_states_box(self.fsm.latest_states, self.ui.expandbox)
        self.hide_widgets(self.ui.square)

    def show_ai_widget(self):
        self.hide_widgets(self.ui.ai)
        self.ui.ai.ai_input.clear()
        self.ui.ai.ai_feedback.setText(
            "<span style='color: gray;'>LLM's feedback will appear here...<br>"
            "Remember the model only answers questions related to building logical squares.</span>"
        )

    def show_solver_widget(self):
        self.hide_widgets(self.ui.solver)
        self.ui.solver_feedback.setText("Note that every new line is considered"
                                        " a new state. Example input can look like this:<br>"
                                        "taxing = true, immobilising = false<br>"
                                        "immobilising = true, engine_stopped = true<br><br>"
                                        "Click on 'Check States' button to verify states."
                                        "Your feedback will appear here...")

    def show_code_widget(self):
        self.hide_widgets(self.ui.code)
        self.ui.smcode.setText("<span style='color: gray;'>Choose code generation "
                               "method from options below.<br>"
                               "Your state machine code will appear here...</span>")

        for button in self.gen_buttons:
            button.setEnabled(True)

    def display_tree_graph(self):
        """
        Rysuje drzewo stanów w widżecie PyQtGraph.
        """
        edges = self.fsm.get_tree_edges()
        node_names = self.fsm.get_state_names()
        gg.draw_tree(self.ui.tree_plot, edges, node_names=node_names)

    def add_square(self):
        a = self.ui.inputA.text() or "true"
        e = self.ui.inputE.text() or "true"
        i = self.ui.inputI.text() or "true"
        o = self.ui.inputO.text() or "true"

        if a == o:
            QtWidgets.QMessageBox.warning(
                self,
                "Data error",
                "Fields 'A' and 'O' cannot have the same value."
            )
            return

        if e == i:
            QtWidgets.QMessageBox.warning(
                self,
                "Data error",
                "Fields 'E' and 'I' cannot have the same value."
            )
            return

        if self.ui.expandbox.isVisible():
            self.parent_id = self.ui.expandbox.currentText()

        self.fsm.add_square(a, e, i, o, self.parent_id)
        self.logger.log(f"Expanded state {self.parent_id} with square with A: {a}, E: {e}, I: {i}, O: {o}")
        self.expanded_states.append(self.parent_id)
        self.remove_transitions_for_expanded_state(self.parent_id)

        if len(self.fsm.latest_states) > 0:
            for input in [self.ui.inputA, self.ui.inputE, self.ui.inputI, self.ui.inputO]:
                input.clear()

            self.show_tree_widget()
            self.show_missing_buttons()
        else:
            return

    def create_expand_widget(self):
        self.ui.expandbox.setVisible(True)
        for widget in [self.ui.add_square_button, self.ui.inputA, self.ui.inputE, self.ui.inputI,
                       self.ui.inputO, self.ui.labelA, self.ui.labelE, self.ui.labelI, self.ui.labelO]:
            geometry = widget.geometry()
            widget.setGeometry(geometry.x(), geometry.y() + 50, geometry.width(), geometry.height())
        self.ui.addsquare.setText("Expand States")
        self.ui.addlabel.setText("Choose a state to expand from box below and "
                                 "replace it with a new logical square. You can "
                                 "only expand the most recent states.")

    def show_missing_buttons(self):
        for button in [
            self.ui.tree_button, self.ui.sm_button, self.ui.assertions_button, self.ui.expand_button,
            self.ui.save_button, self.ui.gen_button, self.ui.solver_button
        ]:
            button.setVisible(True)
        self.ui.square_button.setVisible(False)
        if not self.expanded:
            self.expanded = True
            self.create_expand_widget()

    def fill_states_box(self, item_list, combo_box):
        combo_box.clear()
        for item in item_list:
            combo_box.addItem(str(item))

    def add_name(self):
        state_id = self.ui.namebox.currentText()
        state_name = self.ui.name_input.text()
        self.fsm.assign_name_to_state(state_id, state_name)
        self.logger.log(f"Assigned name {state_name} to state {state_id}")
        self.ui.name_input.clear()
        self.show_tree_widget()

    def update_state_box(self):
        current_state = self.ui.frombox.currentText()

        all_states = [state for state in self.fsm.span_tree.keys() if state not in self.expanded_states]
        existing_transitions = self.fsm.state_transitions_map.get(current_state, {}).values()

        available_states = [state for state in all_states
                            if state not in existing_transitions and state]

        self.ui.tobox.clear()
        for state in available_states:
            self.ui.tobox.addItem(str(state))

    def add_transition(self):
        event = self.ui.ifinput.text()

        if not event.strip():
            return

        from_state = self.ui.frombox.currentText()
        to_state = self.ui.tobox.currentText()

        if to_state:
            self.fsm.add_transition(from_state, to_state, event)
            self.logger.log(f"Added transition from state {from_state} to state {to_state} with event: {event}")
            transitions = [(t[0], t[1], t[2]) for t in self.fsm.transitions]
            all_states = [(state_key, state_data) for state_key, state_data in self.fsm.span_tree.items()
                          if state_key not in self.expanded_states]

            gg.draw_state_machine(self.ui.sm_plot, transitions, all_states)
            self.ui.ifinput.clear()
            self.update_state_box()

    def remove_transitions_for_expanded_state(self, state_id):
        self.fsm.transitions = [transition for transition in self.fsm.transitions
                                if transition[0] != state_id and transition[1] != state_id]

    def sent_request(self):
        prompt = self.ui.ai.ai_input.toPlainText().strip()
        if not prompt:
            return

        self.ui.ai.ai_feedback.clear()
        self.ui.ai.ai_feedback.append("Connecting to agent service...")
        self.ui.send_request_button.setEnabled(False)

        # Connect signals for async updates
        # Disconnect first to avoid duplicate connections
        try:
            self.agent_client.signals.event_received.disconnect()
        except TypeError:
            pass
        try:
            self.agent_client.signals.finished.disconnect()
        except TypeError:
            pass
        try:
            self.agent_client.signals.error.disconnect()
        except TypeError:
            pass

        self.agent_client.signals.event_received.connect(self._on_agent_event)
        self.agent_client.signals.finished.connect(self._on_agent_finished)
        self.agent_client.signals.error.connect(self._on_agent_error)

        # Start async request (non-blocking)
        self.agent_client.send_prompt_async(prompt)

    def _on_agent_event(self, evt):
        """Handle streaming events from agent (runs on main thread via Qt signal)."""
        msg_type = evt.get("type")
        if msg_type == "session":
            session_id = evt.get("session_id", "")
            self.ui.ai.ai_feedback.append(f"Session: {session_id[:20]}...")
        elif msg_type == "error":
            self.ui.ai.ai_feedback.append(f"<b>Error:</b> {evt.get('error')}")
        elif msg_type == "event":
            data = evt.get("data", {})
            node = data.get("node", "unknown")
            step = data.get("step", 0)
            messages = data.get("messages", [])
            state_machine = data.get("state_machine", {})
            states_count = len(state_machine.get("states", []))

            self.ui.ai.ai_feedback.append(f"Step {step}: {node} ({states_count} states)")

            if messages:
                for msg in messages[-1:]:  # Show only latest message
                    content = msg.get("content", "")
                    self.ui.ai.ai_feedback.append(f"  → {content}")

    def _on_agent_finished(self, result):
        """Handle final result from agent (runs on main thread via Qt signal)."""
        self.ui.send_request_button.setEnabled(True)

        messages = result.get("messages", [])
        if messages:
            self.ui.ai.ai_feedback.append("\n<b>Agent Messages:</b>")
            self.ui.ai.ai_feedback.append(aim.format_messages(messages))

        state_machine = result.get("state_machine", {})
        states_count = len(state_machine.get("states", []))
        transitions_count = len(state_machine.get("transitions", []))

        self.ui.ai.ai_feedback.append(
            f"\n<b>Result:</b> {states_count} states, {transitions_count} transitions"
        )

        if state_machine and states_count > 0:
            aim.apply_state_machine_to_fsm(self.fsm, state_machine)
            self.expanded_states = []
            self.ui.ai.ai_feedback.append("States and transitions applied to FSM.")
            self.show_missing_buttons()
        else:
            self.ui.ai.ai_feedback.append("No states generated. Try a different prompt.")

    def _on_agent_error(self, error_msg):
        """Handle error from agent (runs on main thread via Qt signal)."""
        self.ui.send_request_button.setEnabled(True)
        self.ui.ai.ai_feedback.append(f"<b>Request failed:</b> {error_msg}")

    def check_states(self):
        solver_input = self.ui.solver_input.toPlainText()
        states = solver_input.splitlines()
        feedback = solver.check_states_disjoint(states)
        self.ui.solver_feedback.setText(feedback)

    def show_sm_code(self):
        sender = self.sender()

        for button in self.gen_buttons:
            button.setEnabled(True)

        sender.setEnabled(False)
        self.ui.smcode.clear()

        if sender == self.ui.class_button:
            class_code = self.fsm.generate_class_code()
            self.ui.smcode.append(class_code)

        elif sender == self.ui.trans_button:
            transition_code = self.fsm.generate_transition_code()
            self.ui.smcode.append(transition_code)

        elif sender == self.ui.qt_button:
            qt_code = self.fsm.generate_qt_code()
            self.ui.smcode.append(qt_code)

        # elif sender == self.ui.sml_button:
        #     self.fsm.generate_sml()
        #     with open("gen/sml_sm.py", "r") as file:
        #         sml_code = file.read()
        #     self.ui.smcode.append(sml_code)

    def reset_action(self):
        self.close()
        self.__init__()
        self.logger.reset_logs()  # Clear logs
        self.logger.log("Project reset.")  # Log the reset
        self.show()

    def analyze_sm_states_reachability(self):
        pairs = sorted(find_unreachable_pairs_in_state_machine(self.fsm), key=lambda x: x[1])

        self.ui.theorem_prover_feedback.setHtml(
            '<br>'.join([f'<b>{s2}</b> is not reachable from <b>{s1}</b>' for s1, s2 in pairs])
        )
