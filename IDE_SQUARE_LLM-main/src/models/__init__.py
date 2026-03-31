from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class LogicRelationType(str, Enum):
    A = "universal_affirmative"  # All S are P
    E = "universal_negative"  # No S are P
    I = "particular_affirmative"  # Some S are P
    O = "particular_negative"  # Some S are not P


# Model reprezentujący pojedynczą relację logiczną
class LogicRelation(BaseModel):
    relation_type: LogicRelationType
    subject: str
    predicate: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_text: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.relation_type.value}({self.subject}, {self.predicate})"


# Model reprezentujący kwadrat logiczny i jego relacje
class SquareLogicModel(BaseModel):
    relations: List[LogicRelation] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_relation(self, relation: LogicRelation) -> None:
        self.relations.append(relation)
        if relation.subject not in self.entities:
            self.entities.append(relation.subject)
        if relation.predicate not in self.entities:
            self.entities.append(relation.predicate)

    def get_relations_by_type(
        self, relation_type: LogicRelationType
    ) -> List[LogicRelation]:
        return [r for r in self.relations if r.relation_type == relation_type]


class StateTransition(BaseModel):
    from_state: str
    to_state: str
    condition: Optional[str] = None
    action: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class State(BaseModel):
    name: str
    description: Optional[str] = None
    is_initial: bool = False
    is_final: bool = False
    properties: Dict[str, Any] = Field(default_factory=dict)


class StateMachine(BaseModel):
    states: List[State] = Field(default_factory=list)
    transitions: List[StateTransition] = Field(default_factory=list)
    initial_state: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_state(self, state: State) -> None:
        self.states.append(state)
        if state.is_initial:
            self.initial_state = state.name

    def add_transition(self, transition: StateTransition) -> None:
        self.transitions.append(transition)

    def get_state(self, name: str) -> Optional[State]:
        return next((s for s in self.states if s.name == name), None)


class ProofResult(BaseModel):
    is_valid: bool
    proof_time_ms: Optional[int] = None
    prover_output: Optional[str] = None
    counterexample: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class VerificationResult(BaseModel):
    assertion: str
    result: ProofResult
    timestamp: Optional[str] = None


class AgentResponse(BaseModel):
    agent_name: str
    success: bool
    result: Any
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Ontology Models
class OntologyClass(BaseModel):
    name: str
    description: Optional[str] = None
    subclass_of: List[str] = Field(default_factory=list)
    disjoint_with: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class OntologyProperty(BaseModel):
    name: str
    domain: Optional[str] = None  # Class that has this property
    range: Optional[str] = None  # Type/Class of property values
    property_type: str = "data"  # "data" or "object"
    description: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class OntologyModel(BaseModel):
    classes: List[OntologyClass] = Field(default_factory=list)
    properties: List[OntologyProperty] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_class(self, ontology_class: OntologyClass) -> None:
        self.classes.append(ontology_class)

    def add_property(self, ontology_property: OntologyProperty) -> None:
        self.properties.append(ontology_property)

    def get_class(self, name: str) -> Optional[OntologyClass]:
        return next((c for c in self.classes if c.name == name), None)


# Verification Models
class VerificationIssueType(str, Enum):
    LOGIC_INCONSISTENCY = "logic_inconsistency"
    ONTOLOGY_CIRCULAR = "ontology_circular"
    STATE_UNREACHABLE = "state_unreachable"
    CROSS_MODEL_MISMATCH = "cross_model_mismatch"
    DISJOINTNESS_VIOLATION = "disjointness_violation"
    HALLUCINATED_ELEMENT = "hallucinated_element"
    MISSING_STATE = "missing_state"


class VerificationIssue(BaseModel):
    issue_type: VerificationIssueType
    severity: str = "error"  # "error", "warning", "info"
    description: str
    location: Optional[str] = None  # Which model/component
    affected_elements: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VerificationFix(BaseModel):
    issue_id: str
    fix_type: str  # "remove", "add", "modify", "clarify"
    description: str
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    requires_user_input: bool = True


class VerificationReport(BaseModel):
    is_consistent: bool
    issues: List[VerificationIssue] = Field(default_factory=list)
    fixes: List[VerificationFix] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
