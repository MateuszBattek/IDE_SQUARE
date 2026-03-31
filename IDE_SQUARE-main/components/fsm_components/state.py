class State:
    def __init__(self, state_id, assertion, name=None):
        """
        Tworzy nowy stan maszyny stanowej.
        :param state_id: ID stanu
        :param attributes: Atrybuty stanu w postaci słownika (np. {"A": "true", "I": "false"})
        :param assertion: Formuła asercji tego stanu
        """
        self.state_id = state_id
        self.assertion = assertion
        self.name = name

    def assert_state(self):
        """
        Zwraca formułę asercji dla danego stanu.
        """
        return self.assertion

    def __str__(self):
        """
        Zwraca reprezentację stringową stanu.
        """
        if self.name:
            return f"State {self.state_id}: {self.name}, Assertion: {self.assertion}"
        return f"State {self.state_id}, Assertion: {self.assertion}"

    def serialize_state(self):
        return {
            'state_id': self.state_id,
            'assertion': self.assertion,
            'name': self.name
        }
