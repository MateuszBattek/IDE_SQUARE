from components.fsm_components.state import State
from string import ascii_lowercase
from copy import deepcopy
from components.fsm_components.code_generator import (
    generate_class_code,
    generate_transition_code,
    generate_qt_code,
    generate_assertion_code,
)

class LogicalSquareFSM:
    def __init__(self, init_state=None):
        if init_state:
            self.root = init_state['root']
            self.span_tree = init_state['span_tree']
            self.current_id = init_state['current_id']
            self.suffix_index = init_state['suffix_index']
            self.attributes = init_state['attributes']
            self.latest_states = init_state['latest_states']
            self.transitions = init_state['transitions']
            self.state_transitions_map = init_state['state_transitions_map']
            return

        self.span_tree = {}  # Drzewo przechowujące stany i przejścia
        self.root = '0'  # Korzeń drzewa, reprezentuje initial state
        self.span_tree[self.root] = {"state": "State 0", "children": []}
        self.current_id = 1  # Unikalne ID dla każdego stanu
        self.suffix_index = 0
        self.attributes = []
        self.latest_states = []  # Lista ID stanów, które mogą być rozwinięte
        self.transitions = []  # lista przejść
        self.state_transitions_map = {}

    def add_attribute(self, attribute):
        """
        Dodaje atrybut do listy 'attributes' (jeśli nie istnieje już na liście).
        Usuwamy 'not' tylko w przypadku dodawania do listy atrybutów.
        Jeśli wyrażenie zawiera spacje to zamieniamy je na "_"
        :param attribute: Atrybut do dodania.
        """
        attribute_copy = attribute
        if attribute.lower().startswith("not "):
            attribute_copy = attribute[4:].strip()

        if attribute_copy not in self.attributes and attribute_copy != "true":
            self.attributes.append(attribute_copy)

    def get_next_state_id(self):
        """
        Generuje kolejny identyfikator stanu w formacie {kwadrat_counter}{litera}.
        Przykład: 1a, 1b, 1c, 2a, 2b...
        """
        suffix = ascii_lowercase[self.suffix_index]
        state_id = f"{self.current_id}{suffix}"
        self.suffix_index += 1  # Przejście do następnej litery
        return state_id

    def create_logical_square(self, a, e, i, o):
        """
        Tworzy nowy kwadrat logiczny na podstawie interaktywnych danych wejściowych.
        Obsługuje sytuacje pominięcia dowolnego wierzchołka (A, E, I, O).
        :return: Lista stanów [{A, I}, {I, O}, opcjonalnie {O, E}]
        """
        self.add_attribute(a)
        self.add_attribute(e)
        self.add_attribute(i)
        self.add_attribute(o)

        states = []
        self.suffix_index = 0

        # Logika dla pary (A, I)
        if i != "true" and a != "true":
            state_id = self.get_next_state_id()
            state = State(state_id, f"({a} and {i})")
            states.append(state)

        # Logika dla pary (I, O)
        if i != "true" and o != "true":
            state_id = self.get_next_state_id()
            state = State(state_id, f"({i} and {o})")
            states.append(state)

        # Logika dla pary (O, E)
        if o != "true" and e != "true":
            state_id = self.get_next_state_id()
            state = State(state_id, f"({o} and {e})")
            states.append(state)

        self.current_id += 1
        return states

    def assign_name_to_state(self, state_id, name):
        """
        Przypisuje nazwę do istniejącego stanu na podstawie jego ID.
        :param state_id: ID stanu, któremu chcemy przypisać nazwę.
        :param name: Nowa nazwa stanu.
        """
        if state_id in self.span_tree:
            state = self.span_tree[state_id]["state"]
            if isinstance(state, State):
                if len(name) > 0:
                    state.name = name
                    print(f"Przypisano nazwę '{name}' do stanu o ID {state_id}.")
                else:
                    state.name = None
                    print(f"Usunięto nazwę stanu o ID {state_id}.")
            else:
                print(f"Błąd: Stan o ID {state_id} nie jest instancją klasy State.")
        else:
            print(f"Błąd: Nie znaleziono stanu o ID {state_id}.")

    def get_state_names(self):
        """
        Zwraca słownik z nazwami stanów.
        Klucz: ID stanu, Wartość: Nazwa stanu (lub None, jeśli brak nazwy).
        """
        state_names = {}
        for state_id, node_data in self.span_tree.items():
            state = node_data.get("state")
            if isinstance(state, State) and hasattr(state, "assertion"):
                state_names[state_id] = f"Assertion: {state.assertion}"
            if isinstance(state, State) and hasattr(state, "name") and state.name:
                state_names[state_id] = state.name
        return state_names

    def add_square(self, a, e, i, o, parent_id=None):
        """
        Dodaje nowy kwadrat logiczny, rozwijając wybrany stan.
        :param parent_id: ID stanu, który będzie rozwijany
        """

        parent_id = self.root if not parent_id else parent_id

        new_states = self.create_logical_square(a, e, i, o)

        # Aktualizuje drzewo: dodaje dzieci do wybranego stanu
        if parent_id in self.span_tree:
            self.span_tree[parent_id]["children"] = [s.state_id for s in new_states]

        # Dodaje nowe stany jako dzieci
        for state in new_states:
            self.span_tree[state.state_id] = {"state": state, "children": []}

        # Aktualizuje listę najnowszych stanów
        self.latest_states = [s.state_id for s in new_states]

    def display_tree(self, node_id=None, level=0, tree_list=None):
        """
        Zwraca drzewo stanów jako listę zagnieżdżonych stringów.
        """
        if node_id is None:
            node_id = self.root

        node = self.span_tree[node_id]["state"]
        tree_str = " " * (2 * level) + str(node) + "\n"  # Dodajemy nową linię po każdym stanie
        for child_id in self.span_tree[node_id]["children"]:
            tree_str += self.display_tree(child_id, level + 1)

        return tree_str

    def get_tree_edges(self):
        """
        Eksportuje strukturę drzewa jako listę krawędzi.
        """
        edges = []
        for node_id, node_data in self.span_tree.items():
            for child_id in node_data["children"]:
                edges.append((node_id, child_id))
        return edges

    def add_transition(self, from_state, to_state, event):
        """
        Dodaje przejście między stanami i aktualizuje mapę przejść.
        """
        self.transitions.append((from_state, to_state, event))

        if from_state not in self.state_transitions_map:
            self.state_transitions_map[from_state] = {}
        self.state_transitions_map[from_state][event] = to_state

        # return f"State{from_state}  ->  State{to_state}  on event  '{event}'"

    def get_initial_state(self):
        initial_states = [state_id for state_id, node in self.span_tree.items() if not node["children"]]
        initial_state_id = min(initial_states)
        return initial_state_id
    
    


    def generate_class_code(self):
        return generate_class_code(self)

    def generate_assertion_code(self, assertion):
        return generate_assertion_code(assertion)

    def generate_transition_code(self):
        return generate_transition_code(self)

    def generate_qt_code(self):
        return generate_qt_code(self)

    def serialize_object(self):
        return {
            'span_tree': self.serialize_span_tree(),
            'root': self.root,
            'current_id': self.current_id,
            'suffix_index': self.suffix_index,
            'attributes': self.attributes,
            'latest_states': self.latest_states,
            'transitions': self.transitions,
            'state_transitions_map': self.state_transitions_map
        }

    def serialize_span_tree(self):
        result = deepcopy(self.span_tree)
        for key, value in result.items():
            if not isinstance(value['state'], State):
                continue

            result[key]['state'] = value['state'].serialize_state()

        return result

    @classmethod
    def deserialize_logical_square_fsm(cls, fsm_state):
        for key, value in fsm_state['span_tree'].items():
            if type(value['state']) is not str:
                fsm_state['span_tree'][key]['state'] = State(
                    state_id=value['state']['state_id'],
                    assertion=value['state']['assertion'],
                    name=value['state']['name'] if 'name' in value['state'].keys() else None,
                )

        return cls(fsm_state)


