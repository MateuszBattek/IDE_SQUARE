from typing import Dict, Any, Optional, List
from ..agents.base_agent import BaseAgent
from ..models import (
    SquareLogicModel,
    LogicRelation,
    LogicRelationType,
    OntologyClass,
    OntologyProperty,
    OntologyModel,
    ProofResult,
)


class ClassAgent(BaseAgent):
    """
    ClassAgent generates Ontology models from Logic relations.

    Key transformations:
    - A-relations (All X are Y) → subClassOf (X subClassOf Y)
    - E-relations (No X are Y) → disjointWith (X disjointWith Y)
    - I-relations (Some X are Y) → optional properties/relations
    - O-relations (Some X are not Y) → optional exclusions

    Output: JSON structured as OntologyModel
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ClassAgent", config)
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
        Main process method for ClassAgent.

        Input: {"logic_model": {...}}
        Output: {"ontology": {...}, "disjointness_checks": [...]}
        """
        logic_model_data = input_data.get("logic_model")
        if not logic_model_data:
            raise ValueError("No logic model provided")

        # Parse logic model
        if isinstance(logic_model_data, dict):
            logic_model = SquareLogicModel(**logic_model_data)
        else:
            logic_model = logic_model_data

        # Generate ontology
        ontology = await self._build_ontology(logic_model)

        # Check disjointness for E-relations
        disjointness_checks = await self._verify_disjointness(ontology, logic_model)

        return {
            "ontology": ontology.model_dump(),
            "classes_count": len(ontology.classes),
            "properties_count": len(ontology.properties),
            "disjointness_checks": disjointness_checks,
            "all_disjoint_valid": all(
                check.get("result", {}).get("is_valid", False)
                for check in disjointness_checks
            ),
        }

    async def _build_ontology(self, logic_model: SquareLogicModel) -> OntologyModel:
        """
        Build ontology from logic model.

        Process:
        1. Distinguish subjects (classes) from predicates (properties)
        2. Create OntologyClass for entities that appear as subjects
        3. Process A-relations to generate subClassOf
        4. Process E-relations to generate disjointWith
        5. Process I/O-relations to generate properties/notes
        """
        ontology = OntologyModel()
        ontology.metadata["source"] = "ClassAgent"
        ontology.metadata["logic_entities_count"] = len(logic_model.entities)

        # Identify subjects vs predicates
        subjects = set()
        predicates = set()

        for relation in logic_model.relations:
            subjects.add(relation.subject)
            predicates.add(relation.predicate)

        # Entities that are ONLY predicates (never subjects) should be properties
        predicate_only_entities = predicates - subjects

        # Entities that appear as subjects should be classes
        subject_entities = subjects

        # Create classes for subject entities (and predicates that are also subjects)
        for entity in subject_entities:
            ontology_class = OntologyClass(
                name=entity, description=f"Class representing {entity}"
            )
            ontology.add_class(ontology_class)

        # Process relations
        a_relations = logic_model.get_relations_by_type(LogicRelationType.A)
        e_relations = logic_model.get_relations_by_type(LogicRelationType.E)
        i_relations = logic_model.get_relations_by_type(LogicRelationType.I)
        o_relations = logic_model.get_relations_by_type(LogicRelationType.O)

        # Process A-relations: All X are Y
        for relation in a_relations:
            subject_class = ontology.get_class(relation.subject)
            if not subject_class:
                continue

            # If predicate is predicate-only, create a property instead of subclass
            if relation.predicate in predicate_only_entities:
                prop = OntologyProperty(
                    name=f"has_{relation.predicate}",
                    domain=relation.subject,
                    range=relation.predicate,
                    property_type="data",  # or "object" depending on semantics
                    description=f"All {relation.subject} have property {relation.predicate}",
                    confidence=relation.confidence,
                )
                ontology.add_property(prop)
            else:
                # Predicate is also a subject, so it's a valid class - use subClassOf
                if relation.predicate not in subject_class.subclass_of:
                    subject_class.subclass_of.append(relation.predicate)
                    subject_class.properties[f"subClassOf_{relation.predicate}"] = {
                        "confidence": relation.confidence,
                        "source": "A_relation",
                    }

        # Process E-relations: No X are Y
        for relation in e_relations:
            subject_class = ontology.get_class(relation.subject)
            if not subject_class:
                continue

            # If predicate is predicate-only, E-relation doesn't make sense
            # (can't be disjoint with a property)
            if relation.predicate in predicate_only_entities:
                # Skip or create an annotation
                subject_class.properties[f"excludes_{relation.predicate}"] = {
                    "confidence": relation.confidence,
                    "source": "E_relation",
                    "note": f"No {relation.subject} have property {relation.predicate}",
                }
            else:
                # Both are classes - use disjointWith
                if relation.predicate not in subject_class.disjoint_with:
                    subject_class.disjoint_with.append(relation.predicate)
                    subject_class.properties[f"disjointWith_{relation.predicate}"] = {
                        "confidence": relation.confidence,
                        "source": "E_relation",
                    }

                # Also add symmetric disjointness
                predicate_class = ontology.get_class(relation.predicate)
                if predicate_class:
                    if relation.subject not in predicate_class.disjoint_with:
                        predicate_class.disjoint_with.append(relation.subject)

        # Process I-relations: Some X are Y → create property or annotation
        for relation in i_relations:
            prop = OntologyProperty(
                name=f"has_{relation.predicate}",
                domain=relation.subject,
                range=relation.predicate,
                property_type="object",
                description=f"Some {relation.subject} have property {relation.predicate}",
                confidence=relation.confidence,
            )
            ontology.add_property(prop)

        # Process O-relations: Some X are not Y → create exclusion annotation
        for relation in o_relations:
            subject_class = ontology.get_class(relation.subject)
            if subject_class:
                subject_class.properties[f"partial_exclusion_{relation.predicate}"] = {
                    "type": "O_relation",
                    "confidence": relation.confidence,
                    "note": f"Some {relation.subject} are not {relation.predicate}",
                }

        return ontology

    async def _verify_disjointness(
        self, ontology: OntologyModel, logic_model: SquareLogicModel
    ) -> List[Dict[str, Any]]:
        """
        Verify disjointness assertions using ProverAgent.

        For each E-relation (No X are Y), we use ProverAgent to formally verify
        that X and Y are disjoint (¬∃x. X(x) ∧ Y(x)).
        """
        disjointness_checks = []

        e_relations = logic_model.get_relations_by_type(LogicRelationType.E)

        for relation in e_relations:
            # Call ProverAgent to check disjointness
            # Pass the E-relation so ProverAgent can include it as a constraint
            check_input = {
                "task_type": "check_disjointness",
                "class_a": relation.subject,
                "class_b": relation.predicate,
                "e_relation": relation.model_dump(),  # Pass the full E-relation
            }

            result = await self.prover_agent.process(check_input)

            disjointness_checks.append(
                {
                    "relation": {
                        "subject": relation.subject,
                        "predicate": relation.predicate,
                        "type": "E",
                    },
                    "result": result.get("result"),
                    "assertion": result.get("assertion"),
                    "verified": result.get("result", {}).get("is_valid", False),
                }
            )

        return disjointness_checks

    def detect_circular_subclass(self, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """
        Detect circular subclass relationships in the ontology.

        Returns list of circular dependency chains.
        """
        circular_dependencies = []

        def find_cycle(
            class_name: str, visited: set, path: List[str]
        ) -> Optional[List[str]]:
            if class_name in visited:
                # Found a cycle
                cycle_start = path.index(class_name)
                return path[cycle_start:] + [class_name]

            visited.add(class_name)
            path.append(class_name)

            ontology_class = ontology.get_class(class_name)
            if ontology_class:
                for parent in ontology_class.subclass_of:
                    cycle = find_cycle(parent, visited.copy(), path.copy())
                    if cycle:
                        return cycle

            return None

        # Check each class for cycles
        for ontology_class in ontology.classes:
            cycle = find_cycle(ontology_class.name, set(), [])
            if cycle:
                circular_dependencies.append(
                    {
                        "cycle": cycle,
                        "description": f"Circular subclass chain: {' -> '.join(cycle)}",
                    }
                )

        return circular_dependencies

    def validate_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """
        Validate ontology for common issues.

        Checks:
        - Circular subclass relationships
        - Invalid property domains/ranges
        - Conflicting disjointness and subclass
        """
        issues = []

        # Check for circular dependencies
        circular = self.detect_circular_subclass(ontology)
        if circular:
            issues.extend(
                [
                    {"type": "circular_dependency", "severity": "error", **circ}
                    for circ in circular
                ]
            )

        # Check for conflicting disjointness and subclass
        for ontology_class in ontology.classes:
            for parent in ontology_class.subclass_of:
                if parent in ontology_class.disjoint_with:
                    issues.append(
                        {
                            "type": "conflict",
                            "severity": "error",
                            "description": f"Class {ontology_class.name} is both subclass of and disjoint with {parent}",
                        }
                    )

        # Check property domains and ranges exist
        for prop in ontology.properties:
            if prop.domain and not ontology.get_class(prop.domain):
                issues.append(
                    {
                        "type": "invalid_domain",
                        "severity": "warning",
                        "description": f"Property {prop.name} has non-existent domain: {prop.domain}",
                    }
                )

            if prop.range and not ontology.get_class(prop.range):
                issues.append(
                    {
                        "type": "invalid_range",
                        "severity": "warning",
                        "description": f"Property {prop.name} has non-existent range: {prop.range}",
                    }
                )

        return {
            "is_valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "warnings_count": len([i for i in issues if i["severity"] == "warning"]),
            "errors_count": len([i for i in issues if i["severity"] == "error"]),
        }
