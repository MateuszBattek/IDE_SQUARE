from typing import Dict, Any, List, Optional
from ..agents.base_agent import BaseAgent
from ..models import (
    LogicRelation, 
    LogicRelationType, 
    SquareLogicModel,
    State,
    StateTransition,
    StateMachine
)


class LogicAgent(BaseAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("LogicAgent", config)
        self.type_mapping = {
            "universal_affirmative": LogicRelationType.A,
            "universal_negative": LogicRelationType.E,
            "particular_affirmative": LogicRelationType.I,
            "particular_negative": LogicRelationType.O
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = input_data.get("requirements", {})
        if not requirements:
            raise ValueError("No requirements provided from LLMAgent")
        
        logic_model = self._build_logic_model(requirements)
        state_model = self._build_preliminary_state_model(requirements, logic_model)
        contradictions = self._check_square_contradictions(logic_model)
        
        return {
            "logic_model": logic_model.model_dump(),
            "state_model": state_model.model_dump() if state_model else None,
            "entities_found": logic_model.entities,
            "relations_count": len(logic_model.relations),
            "contradictions": contradictions,
            "is_consistent": len(contradictions) == 0
        }
    
    def _build_logic_model(self, requirements: Dict[str, Any]) -> SquareLogicModel:
        logic_model = SquareLogicModel()
        
        formulas = requirements.get("formulas", [])
        for formula in formulas:
            if self._verify_formula(formula):
                relation = self._formula_to_relation(formula)
                if relation:
                    logic_model.add_relation(relation)
        
        entities = requirements.get("entities", [])
        for entity in entities:
            if entity not in logic_model.entities:
                logic_model.entities.append(entity)
        
        logic_model.metadata["source"] = "LLMAgent"
        logic_model.metadata["formula_count"] = len(formulas)
        
        return logic_model
    
    def _verify_formula(self, formula: Dict[str, Any]) -> bool:
        required_fields = ["type", "subject", "predicate"]
        if not all(field in formula for field in required_fields):
            return False
        
        if formula["type"] not in self.type_mapping:
            return False
        
        if not formula["subject"] or not formula["predicate"]:
            return False
        
        if isinstance(formula.get("confidence"), (int, float)):
            if not (0.0 <= formula["confidence"] <= 1.0):
                return False
        
        return True
    
    def _formula_to_relation(self, formula: Dict[str, Any]) -> Optional[LogicRelation]:
        try:
            relation_type = self.type_mapping[formula["type"]]
            
            return LogicRelation(
                relation_type=relation_type,
                subject=formula["subject"].strip(),
                predicate=formula["predicate"].strip(),
                confidence=formula.get("confidence", 1.0),
                source_text=formula.get("source_text", "")
            )
        except (KeyError, ValueError):
            return None
    
    def _build_preliminary_state_model(
        self, 
        requirements: Dict[str, Any], 
        logic_model: SquareLogicModel
    ) -> Optional[StateMachine]:
        states_data = requirements.get("states", [])
        transitions_data = requirements.get("transitions", [])
        
        if not states_data and not transitions_data:
            states_data = self._infer_states_from_logic(logic_model)
        
        if not states_data:
            return None
        
        state_machine = StateMachine()
        
        for i, state_name in enumerate(states_data):
            state = State(
                name=state_name,
                is_initial=(i == 0),
                properties=self._extract_state_properties(state_name, logic_model)
            )
            state_machine.add_state(state)
        
        for transition_data in transitions_data:
            if "from" in transition_data and "to" in transition_data:
                transition = StateTransition(
                    from_state=transition_data["from"],
                    to_state=transition_data["to"],
                    condition=transition_data.get("condition"),
                    confidence=transition_data.get("confidence", 1.0)
                )
                state_machine.add_transition(transition)
        
        state_machine.metadata["source"] = "LogicAgent_preliminary"
        state_machine.metadata["inferred"] = len(states_data) > len(requirements.get("states", []))
        
        return state_machine
    
    def _infer_states_from_logic(self, logic_model: SquareLogicModel) -> List[str]:
        potential_states = []
        
        for entity in logic_model.entities:
            if any(keyword in entity.lower() for keyword in ["state", "status", "phase", "mode"]):
                potential_states.append(entity)
        
        return potential_states
    
    def _extract_state_properties(
        self, 
        state_name: str, 
        logic_model: SquareLogicModel
    ) -> Dict[str, Any]:
        properties = {}
        
        for relation in logic_model.relations:
            if relation.subject == state_name:
                properties[f"has_{relation.predicate}"] = True
            elif relation.predicate == state_name:
                properties[f"is_{relation.subject}"] = True
        
        return properties
    
    def _check_square_contradictions(self, logic_model: SquareLogicModel) -> List[Dict[str, Any]]:
        contradictions = []
        
        a_relations = logic_model.get_relations_by_type(LogicRelationType.A)
        e_relations = logic_model.get_relations_by_type(LogicRelationType.E)
        i_relations = logic_model.get_relations_by_type(LogicRelationType.I)
        o_relations = logic_model.get_relations_by_type(LogicRelationType.O)
        
        for a_rel in a_relations:
            for e_rel in e_relations:
                if (a_rel.subject == e_rel.subject and 
                    a_rel.predicate == e_rel.predicate):
                    contradictions.append({
                        "type": "A_E_contradiction",
                        "description": f"Contradictory: All {a_rel.subject} are {a_rel.predicate} vs No {e_rel.subject} are {e_rel.predicate}",
                        "relations": [str(a_rel), str(e_rel)]
                    })
        
        for a_rel in a_relations:
            for o_rel in o_relations:
                if (a_rel.subject == o_rel.subject and 
                    a_rel.predicate == o_rel.predicate):
                    contradictions.append({
                        "type": "A_O_contradiction",
                        "description": f"Contradictory: All {a_rel.subject} are {a_rel.predicate} vs Some {o_rel.subject} are not {o_rel.predicate}",
                        "relations": [str(a_rel), str(o_rel)]
                    })
        
        for e_rel in e_relations:
            for i_rel in i_relations:
                if (e_rel.subject == i_rel.subject and 
                    e_rel.predicate == i_rel.predicate):
                    contradictions.append({
                        "type": "E_I_contradiction",
                        "description": f"Contradictory: No {e_rel.subject} are {e_rel.predicate} vs Some {i_rel.subject} are {i_rel.predicate}",
                        "relations": [str(e_rel), str(i_rel)]
                    })
        
        a_map = {(r.subject, r.predicate): r for r in a_relations}
        e_map = {(r.subject, r.predicate): r for r in e_relations}
        
        # Sprawdzamy, czy I jest Fałszywe
        i_false_map = {}
        for i_rel in i_relations:
            key = (i_rel.subject, i_rel.predicate)
            if key in e_map:
                i_false_map[key] = {"i_rel": i_rel, "reason": e_map[key]}

        # Sprawdzamy, czy O jest Fałszywe
        o_false_map = {}
        for o_rel in o_relations:
            key = (o_rel.subject, o_rel.predicate)
            if key in a_map:
                o_false_map[key] = {"o_rel": o_rel, "reason": a_map[key]}
                
        # 3. Szukamy sprzeczności: Kiedy I i O są fałszywe dla tego samego (S, P)?
        for key in i_false_map.keys():
            if key in o_false_map:
                s, p = key
                contradictions.append({
                    "type": "I_O_subcontrary_violation",
                    "description": (f"Violation of Subcontrary: 'Some {s} are {p}' (I) is false (due to E), "
                                    f"AND 'Some {s} are not {p}' (O) is false (due to A). "
                                    f"I and O cannot be simultaneously false."),
                    "relations": [
                        str(i_false_map[key]['i_rel']), 
                        str(o_false_map[key]['o_rel']),
                        str(i_false_map[key]['reason']),
                        str(o_false_map[key]['reason'])
                    ]
                })
    
        return contradictions