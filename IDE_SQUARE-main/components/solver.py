import sys
import os

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    z3_dir = os.path.join(base_dir, 'z3', 'lib')
    os.environ['PATH'] = z3_dir + os.pathsep + os.environ['PATH']
    
from z3 import *
import re

variables = {}


def parse_expression(expr_str):
    """Parsuje pojedyncze wyrażenie, np. 'x > 10' lub 'taxing = true'"""
    if expr_str.replace(' ', '').endswith('=true') or expr_str.replace(' ', '').endswith('=false'):
        var_name, value = expr_str.split('=')
        var_name = var_name.strip()
        value = value.strip().lower() == 'true'

        if var_name not in variables:
            variables[var_name] = Bool(var_name)

        return variables[var_name] == value

    match = re.match(r"([a-zA-Z_]+)\s*([<>=!]+)\s*(-?\d+)", expr_str)
    if match:
        var_name, operator, value = match.groups()
        value = int(value)

        if var_name not in variables:
            variables[var_name] = Int(var_name)

        return eval(f"variables['{var_name}'] {operator} {value}")
    raise ValueError(f"Nieprawidłowy format wyrażenia: {expr_str}")


def parse_state(state_str):
    """Parsuje cały stan składający się z wielu warunków"""
    conditions = [parse_expression(expr.strip()) for expr in state_str.split(",")]
    return And(*conditions) if len(conditions) > 1 else conditions[0]


def check_states_disjoint(states):
    """Sprawdza wszystkie pary stanów w liście pod kątem ich rozłączności"""
    parsed_states = [parse_state(state) for state in states]
    solver = Solver()
    feedback = ""

    for i in range(len(parsed_states)):
        for j in range(i + 1, len(parsed_states)):
            solver.push()
            solver.add(And(parsed_states[i], parsed_states[j]))

            if solver.check() == unsat:
                feedback += f"✅ States {i + 1} & {j + 1} are disjoint!\n"
            else:
                feedback += f"❌ States {i + 1} & {j + 1} are NOT disjoint for values:\n"
                feedback += str(solver.model()) + "\n"
            solver.pop()
    return feedback

