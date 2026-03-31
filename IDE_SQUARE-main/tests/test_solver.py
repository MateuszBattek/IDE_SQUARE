import pytest
from components.solver import parse_expression, parse_state, check_states_disjoint

def test_parse_expression_boolean():
    expr1 = "taxing = true"
    expr2 = "immobilising = false"
    
    result1 = parse_expression(expr1)
    result2 = parse_expression(expr2)
    
    assert str(result1) == "taxing == True"
    assert str(result2) == "immobilising == False"

def test_parse_expression_numeric():
    expr1 = "speed > 10"
    expr2 = "temperature <= 25"
    
    result1 = parse_expression(expr1)
    result2 = parse_expression(expr2)
    
    assert str(result1) == "speed > 10"
    assert str(result2) == "temperature <= 25"

def test_parse_state_single_condition():
    state = "taxing = true"
    result = parse_state(state)
    assert str(result) == "taxing == True"

def test_parse_state_multiple_conditions():
    state = "taxing = true, speed > 10"
    result = parse_state(state)
    assert "taxing == True" in str(result)
    assert "speed > 10" in str(result)

def test_check_states_disjoint_disjoint_states():
    states = [
        "taxing = true, speed > 10",
        "taxing = false, speed < 5"
    ]
    result = check_states_disjoint(states)
    assert "✅ States 1 & 2 are disjoint!" in result

def test_check_states_disjoint_overlapping_states():
    states = [
        "taxing = true, speed > 10",
        "taxing = true, speed > 5"
    ]
    result = check_states_disjoint(states)
    assert "❌ States 1 & 2 are NOT disjoint" in result

def test_check_states_disjoint_invalid_expression():
    states = [
        "invalid expression",
        "taxing = true"
    ]
    with pytest.raises(ValueError):
        check_states_disjoint(states)

def test_check_states_disjoint_empty_list():
    states = []
    result = check_states_disjoint(states)
    assert result == ""

def test_check_states_disjoint_single_state():
    states = ["taxing = true"]
    result = check_states_disjoint(states)
    assert result == "" 