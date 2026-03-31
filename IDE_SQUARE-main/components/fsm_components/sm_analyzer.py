from components.fsm_components.fsm import LogicalSquareFSM
from components.theorem_prover import find_unreachable_pairs

def find_unreachable_pairs_in_state_machine(fsm: LogicalSquareFSM) -> list[tuple[str, str]]:
    sm_states = extract_fsm_states(fsm)
    state_index_by_name = {}
    state_name_by_index = {}

    for i, state_name in enumerate(sm_states):
        state_index_by_name[state_name] = i
        state_name_by_index[i] = state_name

    num_states = len(sm_states)
    max_steps = num_states - 1
    transitions = {
        (state_index_by_name[transition[0]], state_index_by_name[transition[1]]) for transition in fsm.transitions
    }

    unreachable_pairs = find_unreachable_pairs(num_states, transitions, max_steps)

    return [(state_name_by_index[i], state_name_by_index[j]) for i,j in unreachable_pairs]



def extract_fsm_states(fsm: LogicalSquareFSM) -> list[str]:
    terminal_states = []
    non_terminal_states = []

    for key, node in fsm.span_tree.items():
        terminal_states.extend(node['children'])
        if len(node['children']) > 0:
            non_terminal_states.append(key)

    return list(set(terminal_states) - set(non_terminal_states))