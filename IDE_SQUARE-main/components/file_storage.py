import json
from typing import Dict, Any, Optional, List

class FileStorage:
    def __init__(self):
        self.data = { 
            'fsm_state': None,
            'solver_example': []
        }

    def save_state(self, file_path: str, fsm_state: Dict[str, Any], solver_example: List[str]) -> bool:
        try:
            self.data['fsm_state'] = fsm_state
            self.data['solver_example'] = solver_example
            
            with open(file_path, 'w') as file:
                json.dump(self.data, file, indent=2)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            raise e

    def load_state(self, file_path: str) -> Optional[tuple[Dict[str, Any], List[str]]]:
        try:
            with open(file_path, 'r') as file:
                loaded_data = json.load(file)
            
            fsm_state = loaded_data.get('fsm_state')
            solver_example = loaded_data.get('solver_example', [])
            
            return fsm_state, solver_example
        except Exception as e:
            print(f"Error loading state: {e}")
            raise e
