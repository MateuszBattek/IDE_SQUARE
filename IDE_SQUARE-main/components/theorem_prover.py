from z3 import *

def create_transition_matrix(num_states, transitions):
    trans = [[Bool(f"t_{i}_{j}") for j in range(num_states)] for i in range(num_states)]
    return trans

def add_transition_constraints(solver, trans, transitions, num_states):
    for i in range(num_states):
        for j in range(num_states):
            solver.add(trans[i][j] == ((i, j) in transitions))

def create_reachability_vars(num_states, max_steps):
    return [[[Bool(f"r_{i}_{j}_{k}") for k in range(max_steps + 1)]
              for j in range(num_states)] for i in range(num_states)]

def add_reachability_constraints(solver, reachable, trans, num_states, max_steps):
    for i in range(num_states):
        for j in range(num_states):
            solver.add(reachable[i][j][0] == (i == j))
    for k in range(1, max_steps + 1):
        for i in range(num_states):
            for j in range(num_states):
                mid_clauses = [And(reachable[i][m][k-1], trans[m][j]) for m in range(num_states)]
                solver.add(reachable[i][j][k] == Or(reachable[i][j][k-1], Or(*mid_clauses)))

def find_unreachable_pairs(num_states, transitions, max_steps):
    solver = Solver()
    trans = create_transition_matrix(num_states, transitions)
    add_transition_constraints(solver, trans, transitions, num_states)
    reachable = create_reachability_vars(num_states, max_steps)
    add_reachability_constraints(solver, reachable, trans, num_states, max_steps)

    unreachable_pairs = []

    for start in range(num_states):
        for end in range(num_states):
            if start == end:
                continue
            solver.push()
            solver.add(Not(reachable[start][end][max_steps]))
            if solver.check() == sat:
                unreachable_pairs.append((start, end))
            solver.pop()

    return unreachable_pairs