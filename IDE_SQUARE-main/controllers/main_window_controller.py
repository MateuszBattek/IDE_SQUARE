from typing import List, Optional, Tuple

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget

from views.gui import Ui_MainWindow
from components.fsm_components.fsm import LogicalSquareFSM
from components.fsm_components.sm_analyzer import find_unreachable_pairs_in_state_machine
from components.fsm_components import graph_gen as gg
from components import ai_module as aim
from components import solver
from components.bot_client import BotServiceClient
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
        self.bot_client = BotServiceClient()

        self.ui.inputA.returnPressed.connect(lambda: self.move_focus(self.ui.inputE))
        self.ui.inputE.returnPressed.connect(lambda: self.move_focus(self.ui.inputI))
        self.ui.inputI.returnPressed.connect(lambda: self.move_focus(self.ui.inputO))
        self.ui.inputO.returnPressed.connect(self._gui_add_square)

        self.ui.add_square_button.clicked.connect(self._gui_add_square)
        self.ui.name_button.clicked.connect(self.show_name_widget)
        self.ui.namebox.currentTextChanged.connect(self.update_assertion)
        self.ui.change_name_button.clicked.connect(self._gui_assign_name)
        self.ui.send_request_button.clicked.connect(self.sent_request)
        self.ui.check_states_button.clicked.connect(self._gui_check_states)

        self.ui.ifinput.returnPressed.connect(self._gui_add_transition)
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
        self.ui.bot_button.clicked.connect(self.show_bot_widget)
        self.ui.bot.send_button.clicked.connect(self.send_bot_message)
        self.ui.bot.prompt_input.installEventFilter(self)
        self._bot_initialized = False
        self.ui.solver_button.clicked.connect(self.show_solver_widget)
        self.ui.gen_button.clicked.connect(self.show_code_widget)

        self.ui.theorem_prover_button.clicked.connect(self._gui_analyze_reachability)

        self.gen_buttons = [self.ui.class_button, self.ui.trans_button, self.ui.qt_button]
        for button in self.gen_buttons:
            button.clicked.connect(self._gui_generate_code)

        self.ui.reset_button.clicked.connect(self.reset_action)

    # ── Core operations (no GUI dependencies — callable by the bot) ───────────

    def add_square(
        self,
        a: str,
        e: str,
        i: str,
        o: str,
        parent_id: Optional[str] = None,
    ) -> Optional[str]:
        """Add a logical square to the FSM.

        Returns an error message string, or None on success.
        """
        a = a or "true"
        e = e or "true"
        i = i or "true"
        o = o or "true"

        if a == o:
            return "Fields 'A' and 'O' cannot have the same value."
        if e == i:
            return "Fields 'E' and 'I' cannot have the same value."

        effective_parent = parent_id if parent_id is not None else self.parent_id
        self.fsm.add_square(a, e, i, o, effective_parent)
        self.logger.log(
            f"Expanded state {effective_parent} with square A:{a} E:{e} I:{i} O:{o}"
        )
        self.expanded_states.append(effective_parent)
        self.remove_transitions_for_expanded_state(effective_parent)
        return None

    def assign_name(self, state_id: str, name: str) -> None:
        """Assign a human-readable name to a state."""
        self.fsm.assign_name_to_state(state_id, name)
        self.logger.log(f"Assigned name '{name}' to state {state_id}")

    def add_transition(
        self, from_state: str, to_state: str, event: str
    ) -> Optional[str]:
        """Add a transition between two states.

        Returns an error message string, or None on success.
        """
        if not event.strip():
            return "Event name cannot be empty."
        if not to_state:
            return "Target state cannot be empty."
        self.fsm.add_transition(from_state, to_state, event)
        self.logger.log(
            f"Added transition {from_state} → {to_state} on event: {event}"
        )
        return None

    def check_states(self, states: List[str]) -> str:
        """Run the disjointness solver on the given state list and return feedback."""
        return solver.check_states_disjoint(states)

    def generate_code(self, format: str) -> str:
        """Generate code for the current FSM.

        format: 'class' | 'transition' | 'qt'
        Returns the generated source code as a string.
        """
        if format == "class":
            return self.fsm.generate_class_code()
        if format == "transition":
            return self.fsm.generate_transition_code()
        if format == "qt":
            return self.fsm.generate_qt_code()
        return ""

    def analyze_reachability(self) -> List[Tuple[str, str]]:
        """Return sorted list of (s1, s2) pairs where s2 is not reachable from s1."""
        return sorted(
            find_unreachable_pairs_in_state_machine(self.fsm), key=lambda x: x[1]
        )

    # ── GUI handlers (read from widgets, delegate to core methods) ────────────

    def _gui_add_square(self) -> None:
        if self.ui.expandbox.isVisible():
            self.parent_id = self.ui.expandbox.currentText()

        error = self.add_square(
            a=self.ui.inputA.text(),
            e=self.ui.inputE.text(),
            i=self.ui.inputI.text(),
            o=self.ui.inputO.text(),
        )

        if error:
            QtWidgets.QMessageBox.warning(self, "Data error", error)
            return

        if self.fsm.latest_states:
            for field in [self.ui.inputA, self.ui.inputE, self.ui.inputI, self.ui.inputO]:
                field.clear()
            self.show_tree_widget()
            self.show_missing_buttons()

    def _gui_assign_name(self) -> None:
        self.assign_name(
            state_id=self.ui.namebox.currentText(),
            name=self.ui.name_input.text(),
        )
        self.ui.name_input.clear()
        self.show_tree_widget()

    def _gui_add_transition(self) -> None:
        error = self.add_transition(
            from_state=self.ui.frombox.currentText(),
            to_state=self.ui.tobox.currentText(),
            event=self.ui.ifinput.text(),
        )
        if error:
            return

        transitions = [(t[0], t[1], t[2]) for t in self.fsm.transitions]
        all_states = [
            (k, v)
            for k, v in self.fsm.span_tree.items()
            if k not in self.expanded_states
        ]
        gg.draw_state_machine(self.ui.sm_plot, transitions, all_states)
        self.ui.ifinput.clear()
        self.update_state_box()

    def _gui_check_states(self) -> None:
        states = self.ui.solver_input.toPlainText().splitlines()
        feedback = self.check_states(states)
        self.ui.solver_feedback.setText(feedback)

    def _gui_generate_code(self) -> None:
        sender = self.sender()
        for button in self.gen_buttons:
            button.setEnabled(True)
        sender.setEnabled(False)
        self.ui.smcode.clear()

        if sender == self.ui.class_button:
            fmt = "class"
        elif sender == self.ui.trans_button:
            fmt = "transition"
        elif sender == self.ui.qt_button:
            fmt = "qt"
        else:
            return

        self.ui.smcode.append(self.generate_code(fmt))

    def _gui_analyze_reachability(self) -> None:
        pairs = self.analyze_reachability()
        self.ui.theorem_prover_feedback.setHtml(
            "<br>".join(
                [f"<b>{s2}</b> is not reachable from <b>{s1}</b>" for s1, s2 in pairs]
            )
        )

    # ── View helpers ──────────────────────────────────────────────────────────

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
                solver_example = [
                    line.strip()
                    for line in self.ui.solver_input.toPlainText().splitlines()
                    if line.strip()
                ]
                self.file_storage.save_state(file_path, fsm_state, solver_example)
                self.logger.log("Saved project to file.")
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
            self.expanded_states = [
                key for key, value in self.fsm.span_tree.items()
                if len(value['children']) != 0
            ]
            if solver_example:
                self.ui.solver_input.setPlainText("\n".join(solver_example))
            if len(self.fsm.latest_states) > 0:
                for field in [self.ui.inputA, self.ui.inputE, self.ui.inputI, self.ui.inputO]:
                    field.clear()
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
        all_state_ids = [
            state_id for state_id in self.fsm.span_tree.keys()
            if state_id not in self.expanded_states
        ]
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
        all_states = [
            (k, v)
            for k, v in self.fsm.span_tree.items()
            if k not in self.expanded_states
        ]
        transitions = [
            (t[0], t[1], t[2])
            for t in self.fsm.transitions
            if isinstance(t, (list, tuple)) and len(t) == 3
        ]
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
        self.ui.solver_feedback.setText(
            "Note that every new line is considered a new state. "
            "Example input can look like this:<br>"
            "taxing = true, immobilising = false<br>"
            "immobilising = true, engine_stopped = true<br><br>"
            "Click on 'Check States' button to verify states. "
            "Your feedback will appear here..."
        )

    def show_code_widget(self):
        self.hide_widgets(self.ui.code)
        self.ui.smcode.setText(
            "<span style='color: gray;'>Choose code generation method from options below.<br>"
            "Your state machine code will appear here...</span>"
        )
        for button in self.gen_buttons:
            button.setEnabled(True)

    def display_tree_graph(self):
        edges = self.fsm.get_tree_edges()
        node_names = self.fsm.get_state_names()
        gg.draw_tree(self.ui.tree_plot, edges, node_names=node_names)

    def create_expand_widget(self):
        self.ui.expandbox.setVisible(True)
        for widget in [
            self.ui.add_square_button,
            self.ui.inputA, self.ui.inputE, self.ui.inputI, self.ui.inputO,
            self.ui.labelA, self.ui.labelE, self.ui.labelI, self.ui.labelO,
        ]:
            geometry = widget.geometry()
            widget.setGeometry(geometry.x(), geometry.y() + 50, geometry.width(), geometry.height())
        self.ui.addsquare.setText("Expand States")
        self.ui.addlabel.setText(
            "Choose a state to expand from box below and replace it with a new logical square. "
            "You can only expand the most recent states."
        )

    def show_missing_buttons(self):
        for button in [
            self.ui.tree_button, self.ui.sm_button, self.ui.assertions_button,
            self.ui.expand_button, self.ui.save_button, self.ui.gen_button,
            self.ui.solver_button,
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

    def update_state_box(self):
        current_state = self.ui.frombox.currentText()
        all_states = [s for s in self.fsm.span_tree.keys() if s not in self.expanded_states]
        existing_targets = self.fsm.state_transitions_map.get(current_state, {}).values()
        available = [s for s in all_states if s not in existing_targets and s]
        self.ui.tobox.clear()
        for state in available:
            self.ui.tobox.addItem(str(state))

    def remove_transitions_for_expanded_state(self, state_id):
        self.fsm.transitions = [
            t for t in self.fsm.transitions
            if t[0] != state_id and t[1] != state_id
        ]

    def reset_action(self):
        self.close()
        self.__init__()
        self.logger.reset_logs()
        self.logger.log("Project reset.")
        self.show()

    # ── Bot ───────────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self.ui.bot.prompt_input:
            if (
                event.type() == QtCore.QEvent.KeyPress
                and event.key() == QtCore.Qt.Key_Return
                and event.modifiers() == QtCore.Qt.ControlModifier
            ):
                self.send_bot_message()
                return True
        return super().eventFilter(obj, event)

    def show_bot_widget(self):
        self.hide_widgets(self.ui.bot)
        if not self._bot_initialized:
            self._bot_initialized = True
            self._bot_append_system(
                "Hello! I'm the IDE Bot. Describe what you'd like to do.<br>"
                "<i>Examples: \"add a transition from 1a to 1b when engine starts\", "
                "\"generate class code\", \"check state disjointness\"</i>"
            )

    def _build_fsm_snapshot(self) -> dict:
        from components.fsm_components.state import State
        states = []
        for sid, data in self.fsm.span_tree.items():
            if sid not in self.expanded_states and isinstance(data["state"], State):
                s = data["state"]
                states.append({
                    "id": sid,
                    "name": s.name or sid,
                    "assertion": getattr(s, "assertion", ""),
                })
        return {
            "states": states,
            "transitions": [
                {"from": t[0], "to": t[1], "event": t[2]}
                for t in self.fsm.transitions
            ],
            "latest_states": self.fsm.latest_states,
        }

    def send_bot_message(self):
        prompt = self.ui.bot.prompt_input.toPlainText().strip()
        if not prompt:
            return
        self.ui.bot.prompt_input.clear()
        self._bot_append_user(prompt)
        self._bot_append_system("Thinking…")
        self.ui.bot.send_button.setEnabled(False)

        try:
            self.bot_client.signals.response_received.disconnect()
        except TypeError:
            pass
        try:
            self.bot_client.signals.error.disconnect()
        except TypeError:
            pass

        self.bot_client.signals.response_received.connect(self._on_bot_response)
        self.bot_client.signals.error.connect(self._on_bot_error)
        self.bot_client.send_message_async(prompt, self._build_fsm_snapshot())

    def _on_bot_response(self, result: dict):
        self.ui.bot.send_button.setEnabled(True)
        operation = result.get("operation", "unknown")
        params = result.get("params", {})
        message = result.get("message", "")

        if message:
            self._bot_append_bot(message)

        if operation == "add_square":
            parent_id = params.get("parent_id")
            if parent_id is None and self.fsm.latest_states:
                parent_id = self.fsm.latest_states[0]
            error = self.add_square(
                a=params.get("a", "true"),
                e=params.get("e", "true"),
                i=params.get("i", "true"),
                o=params.get("o", "true"),
                parent_id=parent_id,
            )
            if error:
                self._bot_append_system(f"Could not add square: {error}")
            else:
                self.show_missing_buttons()
                a, e, i, o = params.get("a","true"), params.get("e","true"), params.get("i","true"), params.get("o","true")
                expanded = f" (expanded state {parent_id})" if parent_id else ""
                self._bot_append_system(f"Done — square added{expanded}: A={a}, E={e}, I={i}, O={o}.")

        elif operation == "assign_name":
            state_id = params.get("state_id") or params.get("state") or params.get("id", "")
            name = params.get("name") or params.get("label", "")
            self.assign_name(state_id=state_id, name=name)
            self._bot_append_system(f"Done — state <b>{state_id}</b> named <b>{name}</b>.")

        elif operation == "add_transition":
            event = (
                params.get("event")
                or params.get("event_name")
                or params.get("label")
                or params.get("trigger")
                or params.get("condition")
                or ""
            )
            if not event:
                self._bot_append_system(
                    "Could not add transition: I understood the states but missed the event name. "
                    "Please repeat with the event explicitly, e.g. \"add transition from 1b to 1c on event 'start engine'\"."
                )
            else:
                from_state = params.get("from_state") or params.get("from", "")
                to_state = params.get("to_state") or params.get("to", "")
                error = self.add_transition(from_state=from_state, to_state=to_state, event=event)
                if error:
                    self._bot_append_system(f"Could not add transition: {error}")
                else:
                    transitions = [(t[0], t[1], t[2]) for t in self.fsm.transitions]
                    all_states = [
                        (k, v)
                        for k, v in self.fsm.span_tree.items()
                        if k not in self.expanded_states
                    ]
                    gg.draw_state_machine(self.ui.sm_plot, transitions, all_states)
                    self._bot_append_system(f"Done — transition <b>{from_state} → {to_state}</b> on event <b>{event}</b>.")

        elif operation == "check_states":
            states = params.get("states", [])
            feedback = self.check_states(states)
            self._bot_append_system(feedback)

        elif operation == "generate_code":
            fmt = params.get("format", "class")
            code = self.generate_code(fmt)
            self._bot_append_system(
                f"<pre style='background:#f5f5f5; padding:6px; white-space:pre-wrap;'>{code}</pre>"
            )

        elif operation == "analyze_reachability":
            pairs = self.analyze_reachability()
            if pairs:
                lines = "<br>".join(
                    f"<b>{s2}</b> is not reachable from <b>{s1}</b>" for s1, s2 in pairs
                )
            else:
                lines = "All states are mutually reachable."
            self._bot_append_system(lines)

        elif operation == "reset":
            self.reset_action()

        elif operation in ("unknown", "error"):
            pass  # message already shown above

    def _on_bot_error(self, error_msg: str):
        self.ui.bot.send_button.setEnabled(True)
        self._bot_append_system(f"Error connecting to agent server: {error_msg}")

    def _bot_append_user(self, text: str):
        self.ui.bot.chat_log.append(
            f"<p style='margin:4px 0;'>"
            f"<span style='color:#1a6fa0;'><b>You:</b></span> {text}"
            f"</p>"
        )
        self._bot_scroll_to_bottom()

    def _bot_append_bot(self, text: str):
        self.ui.bot.chat_log.append(
            f"<p style='margin:4px 0;'>"
            f"<span style='color:#2e7d32;'><b>Bot:</b></span> {text}"
            f"</p>"
        )
        self._bot_scroll_to_bottom()

    def _bot_append_system(self, text: str):
        self.ui.bot.chat_log.append(
            f"<p style='margin:4px 0; color:#888888;'><i>{text}</i></p>"
        )
        self._bot_scroll_to_bottom()

    def _bot_scroll_to_bottom(self):
        sb = self.ui.bot.chat_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── LLM Chat (existing AI panel) ─────────────────────────────────────────

    def sent_request(self):
        prompt = self.ui.ai.ai_input.toPlainText().strip()
        if not prompt:
            return

        self.ui.ai.ai_feedback.clear()
        self.ui.ai.ai_feedback.append("Connecting to agent service...")
        self.ui.send_request_button.setEnabled(False)

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

        self.agent_client.send_prompt_async(prompt)

    def _on_agent_event(self, evt):
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
                for msg in messages[-1:]:
                    content = msg.get("content", "")
                    self.ui.ai.ai_feedback.append(f"  → {content}")

    def _on_agent_finished(self, result):
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
        self.ui.send_request_button.setEnabled(True)
        self.ui.ai.ai_feedback.append(f"<b>Request failed:</b> {error_msg}")