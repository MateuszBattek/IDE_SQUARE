import subprocess
import re


def generate_class_code(fsm):
    """
    Generuje kod klasy maszyny stanowej z dynamicznymi klasami dla aktualnych nierozwiniętych stanów.
    """
    class_code = ""

    # 1. Definiowanie klasy bazowej State
    class_code += "class State:\n"
    class_code += "    def __init__(self, state_id, assertion, name=None):\n"
    class_code += "        self.state_id = state_id\n"
    class_code += "        self.assertion = assertion\n"
    class_code += "        self.name = name\n"
    class_code += "    def handle_event(self, context):\n"
    class_code += "        raise NotImplementedError('Subclasses must implement this method')\n\n\n"

    # 2. Generowanie klas dla aktualnych nierozwiniętych stanów
    for state_id, node in fsm.span_tree.items():
        if not node["children"]:
            state = node["state"]
            class_code += f"class State{state_id}(State):\n"
            class_code += f"    def __init__(self):\n"
            class_code += f"        super().__init__(state_id='{state.state_id}', assertion='{state.assertion}', name='{state.name}')\n\n"
            class_code += f"    def handle_event(self, context):\n"

            # Dodajemy asercje dla stanu (jeśli istnieją)
            state_name_suffix = sanitize_name(state.name) if state and getattr(state, 'name', None) else None
            if state:
                assertion = state.assert_state()
                assertion_code = fsm.generate_assertion_code(assertion)
                if assertion_code:
                    class_code += f"        # Assertion logic\n"
                    class_code += f"        print('State{state_id}: "
                    if state_name_suffix is not None:
                        class_code += f"{state_name_suffix}: "
                    class_code += f"handling event {assertion}')\n"
            class_code += "\n"

            # Logika przejść dla tego stanu
            transitions_for_state = fsm.state_transitions_map.get(state_id, {})
            if transitions_for_state:
                class_code += f"        # Transition logic\n"
                class_code += "        event = context.event\n"
                for event, to_state in transitions_for_state.items():
                    class_code += f"        if event == '{event}':\n"
                    class_code += f"            print('Transitioning to State{to_state}')\n"
                    class_code += f"            context.set_state(State{to_state}())\n"
                    class_code += f"            return\n"
                class_code += f"        print('No valid transition for event')\n"
            else:
                class_code += f"        print('No transitions defined for State{state_id}')\n"
            class_code += "\n\n"

    # 3. Generowanie klasy kontekstowej StateMachineContext
    class_code += "class StateMachineContext:\n"
    class_code += "    def __init__(self):\n"
    class_code += "        # Attributes\n"
    for attribute in fsm.attributes:
        sanitized_attribute = attribute.replace(" ", "_")
        class_code += f"        self.{sanitized_attribute} = False\n"
    class_code += "        self.event = None\n"  # Dodanie eventu w kontekście

    # Ustalanie stanu początkowego
    # initial_states = [state_id for state_id, node in self.span_tree.items() if not node["children"]]
    initial_state_id = fsm.get_initial_state()

    if initial_state_id is not None:
        class_code += f"\n        # Initial state\n"
        class_code += f"        self.current_state = State{initial_state_id}()\n"
    else:
        class_code += f"\n        # Initial state\n"
        class_code += f"        self.current_state = None\n"
        class_code += "        print('Error: No initial state available')\n"

    # Metoda set_state
    class_code += "\n    def set_state(self, state):\n"
    class_code += "        print(f'Transitioning to {state.__class__.__name__}')\n"
    class_code += "        self.current_state = state\n"

    # Metoda handle_event
    class_code += "\n    def handle_event(self, event):\n"
    class_code += "        if self.current_state is None:\n"
    class_code += "            print('Error: No state to handle event')\n"
    class_code += "            return\n"
    class_code += "        self.event = event\n"  # Ustawienie eventu w kontekście
    class_code += "        self.current_state.handle_event(self)\n\n"

    return class_code


def sanitize_name(name):
    cleaned_name = re.sub(r'[^A-Za-z0-9]', '', name.replace(" ", ""))
    return cleaned_name.capitalize()


def generate_assertion_code(assertion):
    """
    Generuje kod dla asercji, zamieniając zmienne na self.<zmienna>.
    Na przykład: (engine on and not door closed) -> (self.engine_on and not self.door_closed).
    """
    if assertion.startswith("(") and assertion.endswith(")"):
        assertion = assertion[1:-1]  # Usuwamy nawiasy na początku i końcu

    tokens = assertion.split()
    processed_tokens = []

    current_variable = []  # Tymczasowa lista do przechowywania zmiennej wielowyrazowej
    for token in tokens:
        if token in {"and", "not"}:
            if current_variable:  # Jeśli wcześniej zgromadzono zmienną
                variable = "_".join(current_variable)  # Łączymy zmienną wielowyrazową za pomocą podkreślnika
                processed_tokens.append(f"context.{variable}")
                current_variable = []  # Reset tymczasowej listy
            processed_tokens.append(token)
        else:
            current_variable.append(token)

    if current_variable:
        variable = "_".join(current_variable)
        processed_tokens.append(f"context.{variable}")

    return " ".join(processed_tokens)


def generate_transition_code(fsm):
    states = []
    for state_id, node in fsm.span_tree.items():
        if not node["children"]:
            state_name = f"State{state_id}"
            states.append(state_name)

    code = "from transitions import Machine\n\n"
    code += "states = " + repr(states) + "\n"
    code += "transitions = [\n"

    for from_state, to_state, event in fsm.transitions:
        code += f"    {{'trigger': '{event}', 'source': '{from_state}', 'dest': '{to_state}'}}, \n"

    initial_id = fsm.get_initial_state()
    code += "]\n\n"
    code += f"machine = Machine(states=states, transitions=transitions, initial='State{initial_id}')\n".format(
        fsm.span_tree[fsm.root].get('state'))

    return code


def generate_qt_code(fsm):
    code = "from PyQt5.QtCore import QState, QStateMachine\n\n"
    code += "machine = QStateMachine()\n\n"

    state_objects = {}
    for state_id, node in fsm.span_tree.items():
        if state_id != 0 and not node['children']:
            obj_name = f"State{state_id}"
            state_objects[state_id] = obj_name
            code += f"{obj_name} = QState()\n"
            code += f"machine.addState({obj_name})\n"

    code += "\n# Define transitions\n"
    for from_state, to_state, event in fsm.transitions:
        print(from_state, to_state, event)
        code += f"{state_objects[from_state]}.addTransition({state_objects[to_state]})\n"

    initial_state_id = fsm.get_initial_state()
    code += "\n# Set initial state\n"
    print(initial_state_id)
    print(state_objects.get(initial_state_id))
    code += f"machine.setInitialState(State{initial_state_id})\n"

    code += "machine.start()\n"
    code += "\n# Example usage:\n"
    code += "print('Qt State Machine initialized and running')\n"

    return code
