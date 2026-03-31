from typing import Dict, Any, Optional, Set, List
import networkx as nx
from ..agents.base_agent import BaseAgent
from ..models import (
    SquareLogicModel,
    StateMachine,
    State,
    StateTransition,
    LogicRelationType,
)
import re


class StateAgent(BaseAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("StateAgent", config)
        self.llm_agent = None  # Will be injected if needed

    def set_llm_agent(self, llm_agent):
        """Inject LLMAgent for intelligent entity classification."""
        self.llm_agent = llm_agent

    async def _classify_entities_with_llm(
        self, 
        entities: List[str], 
        logic_model: SquareLogicModel
    ) -> Dict[str, Dict[str, Any]]:
        """
        Use LLM to classify entities as states or attributes based on semantic context.
        Returns: dict mapping entity -> {"type": "state"|"attribute", "reasoning": str}
        """
        if not self.llm_agent:
            # Fallback to heuristic classification
            return self._heuristic_classify_entities(entities, logic_model)
        
        # Build context from logic relations
        relations_text = "\n".join([
            f"- {r.relation_type.value}: {r.subject} -> {r.predicate} (source: {r.source_text})"
            for r in logic_model.relations
        ])
        
        prompt = f"""
Given the following entities and their logical relations, classify each entity as either a "state" or an "attribute".

States are:
- Concrete objects or entities with a lifecycle (e.g., "flight", "passenger", "room", "order")
- Things that can transition between different conditions
- Nouns representing actors or objects in the system

Attributes are:
- Properties, qualities, or characteristics (e.g., "monitored", "safe", "certified", "available")
- Adjectives or descriptive terms
- Conditions that describe states rather than being states themselves

Entities to classify: {', '.join(entities)}

Logical relations context:
{relations_text}

Respond with a JSON object mapping each entity to its classification:
{{
    "entity_name": {{
        "type": "state" or "attribute",
        "reasoning": "brief explanation"
    }},
    ...
}}
"""
        
        try:
            from ..agents.llm_agent import LLMAgent
            response = await self.llm_agent.client.chat.completions.create(
                model=self.llm_agent.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:].strip()
            if result_text.endswith("```"):
                result_text = result_text[:-3].strip()
            
            import json
            classifications = json.loads(result_text)
            return classifications
        except Exception as e:
            # Fallback to heuristic on error
            return self._heuristic_classify_entities(entities, logic_model)

    def _heuristic_classify_entities(
        self, 
        entities: List[str], 
        logic_model: SquareLogicModel
    ) -> Dict[str, Dict[str, Any]]:
        """
        Heuristic-based classification as fallback.
        Uses linguistic patterns and relation analysis.
        """
        classifications = {}
        
        for entity in entities:
            entity_lower = entity.lower()
            
            # Check morphological patterns
            is_attribute = False
            reasoning = ""
            
            # Common adjective suffixes
            adjective_suffixes = ['ed', 'ing', 'able', 'ible', 'ful', 'less', 'ous', 'ive', 'al', 'ant', 'ent']
            for suffix in adjective_suffixes:
                if entity_lower.endswith(suffix) and len(entity_lower) > len(suffix) + 2:
                    is_attribute = True
                    reasoning = f"Ends with adjective suffix '{suffix}'"
                    break
            
            # Analyze role in relations
            if not is_attribute:
                appears_as_predicate = sum(
                    1 for r in logic_model.relations 
                    if r.predicate == entity and self._looks_like_noun(r.subject)
                )
                appears_as_subject = sum(
                    1 for r in logic_model.relations 
                    if r.subject == entity
                )
                
                # If appears more often as predicate in relations with noun subjects,
                # it's likely an attribute
                if appears_as_predicate > appears_as_subject:
                    is_attribute = True
                    reasoning = "More frequently used as a property/predicate"
            
            classifications[entity] = {
                "type": "attribute" if is_attribute else "state",
                "reasoning": reasoning or "Appears to be a concrete entity/noun"
            }
        
        return classifications

    def _looks_like_noun(self, entity: str) -> bool:
        """Simple heuristic to check if entity looks like a noun."""
        entity_lower = entity.lower()
        # Nouns typically don't end with these suffixes
        non_noun_suffixes = ['ed', 'ing', 'ly']
        return not any(entity_lower.endswith(s) for s in non_noun_suffixes)
    
    async def _extract_states_and_attributes(
        self, 
        logic_model: SquareLogicModel
    ) -> tuple[Set[str], Dict[str, Set[str]]]:
        """
        Extract states and their attributes from the logic model using intelligent classification.
        Returns: (set of states, dict mapping state -> set of attributes)
        """
        # Get all unique entities from relations
        all_entities = set()
        for relation in logic_model.relations:
            all_entities.add(relation.subject)
            all_entities.add(relation.predicate)
        
        # Classify entities using LLM or heuristics
        classifications = await self._classify_entities_with_llm(
            list(all_entities), 
            logic_model
        )
        
        states = set()
        state_attributes = {}  # state_name -> set of attribute names
        
        for relation in logic_model.relations:
            subject = relation.subject
            predicate = relation.predicate
            
            subject_classification = classifications.get(subject, {})
            predicate_classification = classifications.get(predicate, {})
            
            subject_is_state = subject_classification.get("type") == "state"
            predicate_is_state = predicate_classification.get("type") == "state"
            
            # Determine which entity should be a state and which an attribute
            if subject_is_state and not predicate_is_state:
                # Subject is state, predicate is attribute
                states.add(subject)
                if subject not in state_attributes:
                    state_attributes[subject] = set()
                
                # Add attribute based on relation type
                if relation.relation_type == LogicRelationType.A:
                    # All X are Y -> X always has property Y
                    state_attributes[subject].add(f"{predicate}=always")
                elif relation.relation_type == LogicRelationType.I:
                    # Some X are Y -> X can have property Y
                    state_attributes[subject].add(f"{predicate}=possible")
                elif relation.relation_type == LogicRelationType.E:
                    # No X are Y -> X never has property Y
                    state_attributes[subject].add(f"{predicate}=never")
                elif relation.relation_type == LogicRelationType.O:
                    # Some X are not Y -> X sometimes lacks property Y
                    state_attributes[subject].add(f"{predicate}=sometimes_not")
                    
            elif not subject_is_state and predicate_is_state:
                # Predicate is state, subject is attribute (reversed)
                states.add(predicate)
                if predicate not in state_attributes:
                    state_attributes[predicate] = set()
                    
                if relation.relation_type == LogicRelationType.A:
                    state_attributes[predicate].add(f"{subject}=always")
                elif relation.relation_type == LogicRelationType.I:
                    state_attributes[predicate].add(f"{subject}=possible")
                    
            elif subject_is_state and predicate_is_state:
                # Both are states - potential state transition
                states.add(subject)
                states.add(predicate)
            else:
                # If both are attributes or unclear, treat subject as state by default
                # to avoid losing information
                if subject not in states:
                    states.add(subject)
        
        return states, state_attributes

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logic_model_data = input_data.get("logic_model")
        requirements = input_data.get("requirements", {})
        llm_agent = input_data.get("llm_agent")  # Optional LLM agent for classification

        if not logic_model_data:
            raise ValueError("No logic model provided")

        if (
            not isinstance(logic_model_data, dict)
            or "relations" not in logic_model_data
        ):
            raise ValueError("Invalid logic_model structure provided")

        # Inject LLM agent if provided
        if llm_agent:
            self.set_llm_agent(llm_agent)

        logic_model = SquareLogicModel(**logic_model_data)
        state_machine = await self._convert_logic_to_states(logic_model, requirements)

        return {
            "state_machine": state_machine.model_dump(),
            "states_count": len(state_machine.states),
            "transitions_count": len(state_machine.transitions),
        }

    async def _convert_logic_to_states(
        self,
        logic_model: SquareLogicModel,
        requirements: Optional[Dict[str, Any]] = None,
    ) -> StateMachine:
        state_machine = StateMachine()

        # Collect all states from both requirements["states"] and transition endpoints
        state_names = set()
        state_attributes_map = {}  # state -> attributes
        
        # Add explicitly defined states from requirements
        if requirements and "states" in requirements and requirements["states"]:
            state_names.update(requirements["states"])
        
        # Add states from transition endpoints (from/to)
        if requirements and "transitions" in requirements:
            for trans_def in requirements.get("transitions", []):
                if trans_def.get("from"):
                    state_names.add(trans_def["from"])
                if trans_def.get("to"):
                    state_names.add(trans_def["to"])
        
        # If no states found from requirements, extract from logic model
        if not state_names:
            state_names, state_attributes_map = await self._extract_states_and_attributes(logic_model)
        
        state_names = list(state_names)

        # Create states with their attributes
        for state_name in state_names:
            # Get attributes for this state
            attributes = {}
            if state_name in state_attributes_map:
                for attr in state_attributes_map[state_name]:
                    # Parse "attribute_name=value" format
                    if "=" in attr:
                        attr_name, attr_value = attr.split("=", 1)
                        attributes[attr_name] = attr_value
                    else:
                        attributes[attr] = True
            
            state = State(
                name=state_name, 
                description=f"State representing {state_name}",
                properties=attributes
            )
            state_machine.add_state(state)

        # Set initial state if available
        if state_names:
            initial_state = State(name=state_names[0], is_initial=True)
            state_machine.states[0] = initial_state
            state_machine.initial_state = initial_state.name

        # Add explicitly defined transitions from requirements FIRST (if present)
        # These take priority over logic relation conversions
        has_explicit_transitions = False
        if requirements and "transitions" in requirements and requirements["transitions"]:
            for trans_def in requirements["transitions"]:
                from_state = trans_def.get("from")
                to_state = trans_def.get("to")
                condition = trans_def.get("condition", "")

                # Add transition if both states are valid (they should be since we added them above)
                if from_state and to_state:
                    transition = StateTransition(
                        from_state=from_state,
                        to_state=to_state,
                        condition=condition or f"Transition from {from_state} to {to_state}",
                        confidence=0.95,  # High confidence for explicitly defined transitions
                    )
                    state_machine.add_transition(transition)
                    has_explicit_transitions = True

        # Convert logic relations to transitions ONLY if no explicit transitions were provided
        # Only create transitions between actual state entities (not attributes)
        state_names_set = set(state_names)  # For efficient lookup
        if not has_explicit_transitions:
            # Get entity classifications for filtering
            all_entities = set()
            for relation in logic_model.relations:
                all_entities.add(relation.subject)
                all_entities.add(relation.predicate)
            
            classifications = await self._classify_entities_with_llm(
                list(all_entities), 
                logic_model
            )
            
            for relation in logic_model.relations:
                subject = relation.subject
                predicate = relation.predicate
                
                # Only create transitions between actual states, not state-to-attribute relations
                if (
                    subject not in state_names_set
                    or predicate not in state_names_set
                ):
                    continue
                
                # Skip if either entity is classified as an attribute
                subject_is_attribute = classifications.get(subject, {}).get("type") == "attribute"
                predicate_is_attribute = classifications.get(predicate, {}).get("type") == "attribute"
                
                if subject_is_attribute or predicate_is_attribute:
                    continue

                if relation.relation_type == LogicRelationType.A:
                    # Universal affirmative: All A are B
                    # Only create transition if it makes logical sense
                    # (e.g., "All reservations become confirmed" makes sense,
                    #  but "All rooms are clean" should be an attribute, not transition)
                    transition = StateTransition(
                        from_state=subject,
                        to_state=predicate,
                        condition=f"universal: all {subject} are {predicate}",
                        confidence=relation.confidence,
                    )
                    state_machine.add_transition(transition)

                elif relation.relation_type == LogicRelationType.E:
                    # Universal negative: No A are B -> A excludes B (no transition)
                    # We could represent this with metadata or constraints
                    state_machine.metadata.setdefault("exclusions", []).append(
                        {
                            "from": subject,
                            "to": predicate,
                            "type": "universal_negative",
                        }
                    )

                elif relation.relation_type == LogicRelationType.I:
                    # Particular affirmative: Some A are B -> possible transition
                    # Only if both are states, not attributes
                    transition = StateTransition(
                        from_state=subject,
                        to_state=predicate,
                        condition=f"possible: some {subject} are {predicate}",
                        confidence=relation.confidence * 0.5,  # Lower confidence for partial relations
                    )
                    state_machine.add_transition(transition)

                elif relation.relation_type == LogicRelationType.O:
                    # Particular negative: Some A are not B -> conditional exclusion
                    state_machine.metadata.setdefault("partial_exclusions", []).append(
                        {
                            "from": subject,
                            "to": predicate,
                            "type": "particular_negative",
                        }
                    )

        return state_machine
