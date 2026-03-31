import pytest
from components.solver import variables

@pytest.fixture(autouse=True)
def clear_variables():
    """Clear the variables dictionary before each test."""
    variables.clear()
    yield
    variables.clear() 