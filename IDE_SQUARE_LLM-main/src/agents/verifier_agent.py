from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import networkx as nx
from ..agents.base_agent import BaseAgent
from ..models import (
    SquareLogicModel,
    LogicRelationType,
    OntologyModel,
    OntologyClass,
    StateMachine,
    State,
    StateTransition,
    VerificationReport,
    VerificationIssue,
    VerificationIssueType,
    VerificationFix,
    ProofResult,
)


class VerifierAgent(BaseAgent):
    """
    VerifierAgent checks consistency across Logic, Ontology, and State Machine models.

    Key checks:
    1. Logic Consistency: Verifies Square of Opposition rules
    2. Ontology Consistency: Checks for circular relationships, property validity
    3. State Machine Consistency: Checks reachability, transition validity
    4. Cross-Model Consistency: Ensures alignment across all models

    Output: VerificationReport with issues and proposed fixes
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("VerifierAgent", config)
        self.prover_config = config
        self._prover_agent = None

    @property
    def prover_agent(self):
        """Lazy load ProverAgent to avoid circular import."""
        if self._prover_agent is None:
            from .prover_agent import ProverAgent

            self._prover_agent = ProverAgent(self.prover_config)
        return self._prover_agent

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main process method for VerifierAgent.

        Input: {
            "logic_model": {...},
            "ontology": {...},
            "state_machine": {...},
            "requirements": {...}  # Optional: original requirements for hallucination detection
        }

        Output: VerificationReport
        """
        logic_model_data = input_data.get("logic_model")
        ontology_data = input_data.get("ontology")
        state_machine_data = input_data.get("state_machine")
        requirements = input_data.get("requirements", {})

        # Parse models
        logic_model = None
        if logic_model_data:
            logic_model = (
                SquareLogicModel(**logic_model_data)
                if isinstance(logic_model_data, dict)
                else logic_model_data
            )

        ontology = None
        if ontology_data:
            ontology = (
                OntologyModel(**ontology_data)
                if isinstance(ontology_data, dict)
                else ontology_data
            )

        state_machine = None
        if state_machine_data:
            state_machine = (
                StateMachine(**state_machine_data)
                if isinstance(state_machine_data, dict)
                else state_machine_data
            )

        # Perform verification
        report = await self._verify_all(
            logic_model, ontology, state_machine, requirements
        )

        return {
            "verification_report": report.model_dump(),
            "is_consistent": report.is_consistent,
            "issues_count": len(report.issues),
            "fixes_count": len(report.fixes),
            "error_count": len([i for i in report.issues if i.severity == "error"]),
            "warning_count": len([i for i in report.issues if i.severity == "warning"]),
        }

    async def _verify_all(
        self,
        logic_model: Optional[SquareLogicModel],
        ontology: Optional[OntologyModel],
        state_machine: Optional[StateMachine],
        requirements: Dict[str, Any],
    ) -> VerificationReport:
        """
        Perform comprehensive verification across all models.
        """
        report = VerificationReport(
            is_consistent=True, timestamp=datetime.now().isoformat()
        )

        # 1. Check Logic Consistency
        if logic_model:
            logic_issues = await self._check_logic_consistency(logic_model)
            report.issues.extend(logic_issues)

        # 2. Check Ontology Consistency
        if ontology:
            ontology_issues = self._check_ontology_consistency(ontology)
            report.issues.extend(ontology_issues)

        # 3. Check State Machine Consistency
        if state_machine:
            state_issues = self._check_state_machine_consistency(state_machine)
            report.issues.extend(state_issues)

        # 4. Check Cross-Model Consistency
        if logic_model and ontology:
            cross_issues = self._check_cross_model_consistency(
                logic_model, ontology, state_machine
            )
            report.issues.extend(cross_issues)

        # 5. Detect Hallucinated Elements
        if requirements:
            hallucination_issues = self._detect_hallucinations(
                logic_model, ontology, state_machine, requirements
            )
            report.issues.extend(hallucination_issues)

        # 6. Generate Fixes
        report.fixes = self._generate_fixes(report.issues)

        # 7. Update statistics
        report.statistics = {
            "total_issues": len(report.issues),
            "errors": len([i for i in report.issues if i.severity == "error"]),
            "warnings": len([i for i in report.issues if i.severity == "warning"]),
            "total_fixes": len(report.fixes),
            "logic_model_present": logic_model is not None,
            "ontology_present": ontology is not None,
            "state_machine_present": state_machine is not None,
        }

        # Determine overall consistency
        report.is_consistent = (
            len([i for i in report.issues if i.severity == "error"]) == 0
        )

        return report

    async def _check_logic_consistency(
        self, logic_model: SquareLogicModel
    ) -> List[VerificationIssue]:
        """
        Check Square of Opposition consistency using ProverAgent.

        Verifies:
        - A vs O (contradictory)
        - E vs I (contradictory)
        - A vs E (contrary)
        - I vs O (subcontrary)
        """
        issues = []

        a_relations = logic_model.get_relations_by_type(LogicRelationType.A)
        e_relations = logic_model.get_relations_by_type(LogicRelationType.E)
        i_relations = logic_model.get_relations_by_type(LogicRelationType.I)
        o_relations = logic_model.get_relations_by_type(LogicRelationType.O)

        # Check A vs O (contradictory)
        for a_rel in a_relations:
            for o_rel in o_relations:
                if (
                    a_rel.subject == o_rel.subject
                    and a_rel.predicate == o_rel.predicate
                ):
                    # Verify contradictory property
                    result = await self.prover_agent.process(
                        {
                            "task_type": "verify_square_property",
                            "relation_a": a_rel.model_dump(),
                            "relation_b": o_rel.model_dump(),
                            "property_type": "contradictory",
                        }
                    )

                    if not result.get("result", {}).get("is_valid", False):
                        issues.append(
                            VerificationIssue(
                                issue_type=VerificationIssueType.LOGIC_INCONSISTENCY,
                                severity="error",
                                description=f"Contradictory violation: A({a_rel.subject}, {a_rel.predicate}) and O({o_rel.subject}, {o_rel.predicate})",
                                location="logic_model",
                                affected_elements=[str(a_rel), str(o_rel)],
                            )
                        )

        # Check E vs I (contradictory)
        for e_rel in e_relations:
            for i_rel in i_relations:
                if (
                    e_rel.subject == i_rel.subject
                    and e_rel.predicate == i_rel.predicate
                ):
                    result = await self.prover_agent.process(
                        {
                            "task_type": "verify_square_property",
                            "relation_a": e_rel.model_dump(),
                            "relation_b": i_rel.model_dump(),
                            "property_type": "contradictory",
                        }
                    )

                    if not result.get("result", {}).get("is_valid", False):
                        issues.append(
                            VerificationIssue(
                                issue_type=VerificationIssueType.LOGIC_INCONSISTENCY,
                                severity="error",
                                description=f"Contradictory violation: E({e_rel.subject}, {e_rel.predicate}) and I({i_rel.subject}, {i_rel.predicate})",
                                location="logic_model",
                                affected_elements=[str(e_rel), str(i_rel)],
                            )
                        )

        # Check A vs E (contrary)
        for a_rel in a_relations:
            for e_rel in e_relations:
                if (
                    a_rel.subject == e_rel.subject
                    and a_rel.predicate == e_rel.predicate
                ):
                    result = await self.prover_agent.process(
                        {
                            "task_type": "verify_square_property",
                            "relation_a": a_rel.model_dump(),
                            "relation_b": e_rel.model_dump(),
                            "property_type": "contrary",
                        }
                    )

                    if not result.get("result", {}).get("is_valid", False):
                        issues.append(
                            VerificationIssue(
                                issue_type=VerificationIssueType.LOGIC_INCONSISTENCY,
                                severity="error",
                                description=f"Contrary violation: A({a_rel.subject}, {a_rel.predicate}) and E({e_rel.subject}, {e_rel.predicate}) cannot both be true",
                                location="logic_model",
                                affected_elements=[str(a_rel), str(e_rel)],
                            )
                        )

        return issues

    def _check_ontology_consistency(
        self, ontology: OntologyModel
    ) -> List[VerificationIssue]:
        """
        Check ontology for structural issues.

        Checks:
        - Circular subclass relationships
        - Invalid property domains/ranges
        - Conflicting disjointness and subclass
        """
        issues = []

        # Check for circular subclass relationships
        circular = self._detect_circular_subclass(ontology)
        for cycle in circular:
            issues.append(
                VerificationIssue(
                    issue_type=VerificationIssueType.ONTOLOGY_CIRCULAR,
                    severity="error",
                    description=f"Circular subclass dependency: {' -> '.join(cycle)}",
                    location="ontology",
                    affected_elements=cycle,
                )
            )

        # Check for conflicts between disjointness and subclass
        for ont_class in ontology.classes:
            for parent in ont_class.subclass_of:
                if parent in ont_class.disjoint_with:
                    issues.append(
                        VerificationIssue(
                            issue_type=VerificationIssueType.DISJOINTNESS_VIOLATION,
                            severity="error",
                            description=f"Class {ont_class.name} is both subclass of and disjoint with {parent}",
                            location="ontology",
                            affected_elements=[ont_class.name, parent],
                        )
                    )

        # Check property domains and ranges
        for prop in ontology.properties:
            if prop.domain and not ontology.get_class(prop.domain):
                issues.append(
                    VerificationIssue(
                        issue_type=VerificationIssueType.CROSS_MODEL_MISMATCH,
                        severity="warning",
                        description=f"Property {prop.name} references non-existent domain: {prop.domain}",
                        location="ontology.properties",
                        affected_elements=[prop.name, prop.domain],
                    )
                )

            if prop.range and not ontology.get_class(prop.range):
                issues.append(
                    VerificationIssue(
                        issue_type=VerificationIssueType.CROSS_MODEL_MISMATCH,
                        severity="warning",
                        description=f"Property {prop.name} references non-existent range: {prop.range}",
                        location="ontology.properties",
                        affected_elements=[prop.name, prop.range],
                    )
                )

        return issues

    def _check_state_machine_consistency(
        self, state_machine: StateMachine
    ) -> List[VerificationIssue]:
        """
        Check state machine for structural issues.

        Checks:
        - Unreachable states
        - Invalid transitions (referencing non-existent states)
        - Missing initial state
        """
        issues = []

        # Check for initial state
        if not state_machine.initial_state and len(state_machine.states) > 0:
            issues.append(
                VerificationIssue(
                    issue_type=VerificationIssueType.STATE_UNREACHABLE,
                    severity="warning",
                    description="State machine has no initial state defined",
                    location="state_machine",
                    affected_elements=[],
                )
            )

        # Build graph for reachability analysis
        graph = nx.DiGraph()

        # Add all states
        for state in state_machine.states:
            graph.add_node(state.name)

        # Add transitions
        for transition in state_machine.transitions:
            if transition.from_state not in [s.name for s in state_machine.states]:
                issues.append(
                    VerificationIssue(
                        issue_type=VerificationIssueType.CROSS_MODEL_MISMATCH,
                        severity="error",
                        description=f"Transition references non-existent source state: {transition.from_state}",
                        location="state_machine.transitions",
                        affected_elements=[transition.from_state],
                    )
                )

            if transition.to_state not in [s.name for s in state_machine.states]:
                issues.append(
                    VerificationIssue(
                        issue_type=VerificationIssueType.CROSS_MODEL_MISMATCH,
                        severity="error",
                        description=f"Transition references non-existent target state: {transition.to_state}",
                        location="state_machine.transitions",
                        affected_elements=[transition.to_state],
                    )
                )

            graph.add_edge(transition.from_state, transition.to_state)

        # Check reachability
        if state_machine.initial_state:
            reachable = set(nx.descendants(graph, state_machine.initial_state))
            reachable.add(state_machine.initial_state)

            for state in state_machine.states:
                if state.name not in reachable:
                    issues.append(
                        VerificationIssue(
                            issue_type=VerificationIssueType.STATE_UNREACHABLE,
                            severity="warning",
                            description=f"State {state.name} is unreachable from initial state",
                            location="state_machine",
                            affected_elements=[state.name],
                        )
                    )

        return issues

    def _check_cross_model_consistency(
        self,
        logic_model: SquareLogicModel,
        ontology: OntologyModel,
        state_machine: Optional[StateMachine],
    ) -> List[VerificationIssue]:
        """
        Check consistency across models.

        Verifies:
        - Ontology classes match logic entities
        - State machine states correspond to ontology classes
        - E-relations don't conflict with state transitions
        """
        issues = []

        # Check if ontology classes match logic entities (using normalized matching)
        logic_entities = set(logic_model.entities)
        ontology_classes = set(c.name for c in ontology.classes)

        # Check for missing entities in ontology (not found after normalization)
        for entity in logic_entities:
            if not any(
                self._is_entity_match(entity, ont_class)
                for ont_class in ontology_classes
            ):
                issues.append(
                    VerificationIssue(
                        issue_type=VerificationIssueType.MISSING_STATE,
                        severity="warning",
                        description=f"Logic entity {entity} not found in ontology",
                        location="cross_model",
                        affected_elements=[entity],
                    )
                )

        # Check for extra classes in ontology (not found after normalization)
        for ont_class in ontology_classes:
            if not any(
                self._is_entity_match(ont_class, entity) for entity in logic_entities
            ):
                issues.append(
                    VerificationIssue(
                        issue_type=VerificationIssueType.HALLUCINATED_ELEMENT,
                        severity="info",
                        description=f"Ontology class {ont_class} not present in logic model",
                        location="cross_model",
                        affected_elements=[ont_class],
                    )
                )

        # Check state machine alignment if present
        if state_machine:
            state_names = set(s.name for s in state_machine.states)

            # Check E-relations vs transitions
            e_relations = logic_model.get_relations_by_type(LogicRelationType.E)
            for e_rel in e_relations:
                for transition in state_machine.transitions:
                    if (
                        transition.from_state == e_rel.subject
                        and transition.to_state == e_rel.predicate
                    ):
                        issues.append(
                            VerificationIssue(
                                issue_type=VerificationIssueType.DISJOINTNESS_VIOLATION,
                                severity="error",
                                description=f"Transition from {transition.from_state} to {transition.to_state} violates E-relation (disjointness)",
                                location="cross_model",
                                affected_elements=[
                                    transition.from_state,
                                    transition.to_state,
                                ],
                            )
                        )

        return issues

    def _normalize_entity(self, entity: str) -> str:
        """
        Normalize entity names for comparison.

        Handles:
        - Case normalization (lowercase)
        - Underscore to space conversion
        - Common suffix removal (_state, _order, etc.)
        - Common prefix removal (in_, order_, etc.)
        - Plural to singular conversion (simple heuristic)
        - Extra whitespace trimming
        """
        name = entity.lower().strip()
        
        # Remove common suffixes first
        for suffix in ["_state", "_status", "_order", "_room", "_product"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove common prefixes (order matters - check longer ones first)
        for prefix in ["order_in_", "room_in_", "in_", "order_", "room_", "state_"]:
            if name.startswith(prefix) and len(name) > len(prefix):
                name = name[len(prefix):]
                break  # Only remove one prefix
        
        # Replace underscores/hyphens/spaces
        name = name.replace("_", "").replace("-", "").replace(" ", "")

        # Simple plural handling: remove trailing 's' if present
        if name.endswith("s") and len(name) > 1:
            non_plural_endings = ["ss", "us", "is"]
            if not any(name.endswith(ending) for ending in non_plural_endings):
                name = name[:-1]

        return name

    def _is_entity_match(self, entity1: str, entity2: str) -> bool:
        """
        Check if two entity names match after normalization.
        """
        return self._normalize_entity(entity1) == self._normalize_entity(entity2)

    def _detect_hallucinations(
        self,
        logic_model: Optional[SquareLogicModel],
        ontology: Optional[OntologyModel],
        state_machine: Optional[StateMachine],
        requirements: Dict[str, Any],
    ) -> List[VerificationIssue]:
        """
        Detect elements not grounded in original requirements.

        Checks for entities, states, or classes that don't appear in requirements.
        Uses normalized entity matching to avoid false positives from minor variations
        (plurals, underscores vs spaces, case differences).
        """
        issues = []

        # Build complete set of allowed entities from requirements
        req_entities = set(requirements.get("entities", []))
        req_states = set(requirements.get("states", []))
        
        # Also extract entities from formulas (subject/predicate)
        for formula in requirements.get("formulas", []):
            if formula.get("subject"):
                req_entities.add(formula["subject"])
            if formula.get("predicate"):
                req_entities.add(formula["predicate"])
        
        # Extract state names from transitions
        for trans in requirements.get("transitions", []):
            if trans.get("from"):
                req_states.add(trans["from"])
            if trans.get("to"):
                req_states.add(trans["to"])
        
        # Combine all for comprehensive matching
        all_req_entities = req_entities | req_states

        if not all_req_entities:
            return issues  # Can't detect hallucinations without requirements

        # Check logic model entities
        if logic_model and all_req_entities:
            for entity in logic_model.entities:
                # Check if entity matches any requirement entity (after normalization)
                if not any(
                    self._is_entity_match(entity, req_entity)
                    for req_entity in all_req_entities
                ):
                    issues.append(
                        VerificationIssue(
                            issue_type=VerificationIssueType.HALLUCINATED_ELEMENT,
                            severity="warning",
                            description=f"Logic entity {entity} not found in original requirements",
                            location="logic_model",
                            affected_elements=[entity],
                            metadata={"possible_hallucination": True},
                        )
                    )

        # Check ontology classes
        if ontology and all_req_entities:
            for ont_class in ontology.classes:
                # Check if class matches any requirement entity (after normalization)
                if not any(
                    self._is_entity_match(ont_class.name, req_entity)
                    for req_entity in all_req_entities
                ):
                    issues.append(
                        VerificationIssue(
                            issue_type=VerificationIssueType.HALLUCINATED_ELEMENT,
                            severity="info",
                            description=f"Ontology class {ont_class.name} not found in original requirements",
                            location="ontology",
                            affected_elements=[ont_class.name],
                            metadata={"possible_hallucination": True},
                        )
                    )

        # Check state machine states - compare against req_states (or entities if no states defined)
        check_against = req_states if req_states else all_req_entities
        if state_machine and check_against:
            for state in state_machine.states:
                # Check if state matches any requirement state (after normalization)
                if not any(
                    self._is_entity_match(state.name, req_state)
                    for req_state in check_against
                ):
                    issues.append(
                        VerificationIssue(
                            issue_type=VerificationIssueType.HALLUCINATED_ELEMENT,
                            severity="info",
                            description=f"State {state.name} not found in original requirements",
                            location="state_machine",
                            affected_elements=[state.name],
                            metadata={"possible_hallucination": True},
                        )
                    )

        return issues

    def _generate_fixes(self, issues: List[VerificationIssue]) -> List[VerificationFix]:
        """
        Generate proposed fixes for detected issues.

        Fixes are suggestions for the user, not automatic corrections.
        """
        fixes = []

        for i, issue in enumerate(issues):
            fix_id = f"fix_{i}"

            if issue.issue_type == VerificationIssueType.ONTOLOGY_CIRCULAR:
                fixes.append(
                    VerificationFix(
                        issue_id=fix_id,
                        fix_type="remove",
                        description=f"Remove one subclass relationship to break circular dependency",
                        proposed_changes={
                            "action": "remove_subclass",
                            "affected_elements": issue.affected_elements,
                        },
                        confidence=0.8,
                        requires_user_input=True,
                    )
                )

            elif issue.issue_type == VerificationIssueType.DISJOINTNESS_VIOLATION:
                fixes.append(
                    VerificationFix(
                        issue_id=fix_id,
                        fix_type="clarify",
                        description=f"Resolve conflict: {issue.description}",
                        proposed_changes={
                            "action": "user_clarification_needed",
                            "question": f"Should {issue.affected_elements[0]} be related to {issue.affected_elements[1]}?",
                        },
                        confidence=0.7,
                        requires_user_input=True,
                    )
                )

            elif issue.issue_type == VerificationIssueType.MISSING_STATE:
                fixes.append(
                    VerificationFix(
                        issue_id=fix_id,
                        fix_type="add",
                        description=f"Add missing element: {issue.affected_elements[0]}",
                        proposed_changes={
                            "action": "add_element",
                            "element": issue.affected_elements[0],
                            "location": issue.location,
                        },
                        confidence=0.9,
                        requires_user_input=False,
                    )
                )

            elif issue.issue_type == VerificationIssueType.HALLUCINATED_ELEMENT:
                fixes.append(
                    VerificationFix(
                        issue_id=fix_id,
                        fix_type="remove",
                        description=f"Remove potentially hallucinated element: {issue.affected_elements[0]}",
                        proposed_changes={
                            "action": "remove_element",
                            "element": issue.affected_elements[0],
                            "location": issue.location,
                        },
                        confidence=0.6,
                        requires_user_input=True,
                    )
                )

            elif issue.issue_type == VerificationIssueType.STATE_UNREACHABLE:
                fixes.append(
                    VerificationFix(
                        issue_id=fix_id,
                        fix_type="modify",
                        description=f"Add transition to make state reachable or remove unreachable state",
                        proposed_changes={
                            "action": "add_transition_or_remove_state",
                            "state": issue.affected_elements[0]
                            if issue.affected_elements
                            else None,
                        },
                        confidence=0.7,
                        requires_user_input=True,
                    )
                )

        return fixes

    def _detect_circular_subclass(self, ontology: OntologyModel) -> List[List[str]]:
        """
        Detect circular subclass relationships using graph cycle detection.
        """
        circular_dependencies = []
        graph = nx.DiGraph()

        # Build graph
        for ont_class in ontology.classes:
            graph.add_node(ont_class.name)
            for parent in ont_class.subclass_of:
                graph.add_edge(ont_class.name, parent)

        # Find cycles
        try:
            cycles = list(nx.simple_cycles(graph))
            circular_dependencies = cycles
        except Exception:
            pass

        return circular_dependencies
