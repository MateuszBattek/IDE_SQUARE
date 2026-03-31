from typing import Dict, Any, Optional, Tuple
import time
import z3
from ..agents.base_agent import BaseAgent
from ..models import ProofResult, LogicRelationType


class ProverAgent(BaseAgent):
    """
    ProverAgent integrates Z3 theorem prover for formal verification.

    Key functions:
    - check_disjointness_z3: Verifies if two classes are disjoint
    - check_satisfiability_z3: Checks if a formula is satisfiable
    - verify_square_property_z3: Verifies Square of Opposition properties
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("ProverAgent", config)
        self.timeout = self.config.get("timeout_ms", 5000)  # Default 5 seconds

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main process method for ProverAgent.

        Supports different verification tasks:
        - check_disjointness: Check if two classes are disjoint
        - check_satisfiability: Check if a formula is satisfiable
        - verify_square_property: Verify Square of Opposition rules
        """
        task_type = input_data.get("task_type", "check_disjointness")

        if task_type == "check_disjointness":
            return await self._check_disjointness(input_data)
        elif task_type == "check_satisfiability":
            return await self._check_satisfiability(input_data)
        elif task_type == "verify_square_property":
            return await self._verify_square_property(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _check_disjointness(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if two classes are disjoint using Z3.

        Input: {
            "class_a": "ClassA", 
            "class_b": "ClassB",
            "e_relation": {...}  # Optional: E-relation that asserts disjointness
        }

        Returns ProofResult indicating if classes are disjoint.
        SAT = classes overlap (not disjoint)
        UNSAT = classes are disjoint
        """
        class_a = input_data.get("class_a")
        class_b = input_data.get("class_b")
        e_relation = input_data.get("e_relation")  # Optional E-relation constraint

        if not class_a or not class_b:
            raise ValueError("Both class_a and class_b must be provided")

        result = self.check_disjointness_z3(class_a, class_b, e_relation)

        return {
            "assertion": f"disjoint({class_a}, {class_b})",
            "result": result.model_dump(),
            "classes": [class_a, class_b],
        }

    async def _check_satisfiability(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a logical formula is satisfiable.

        Input: {"formula": "formula_description", "constraints": [...]}
        """
        formula_desc = input_data.get("formula", "")
        constraints = input_data.get("constraints", [])

        result = self.check_satisfiability_z3(formula_desc, constraints)

        return {
            "assertion": formula_desc,
            "result": result.model_dump(),
            "constraints": constraints,
        }

    async def _verify_square_property(
        self, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify Square of Opposition properties.

        Input: {
            "relation_a": {...},  # A-type relation
            "relation_b": {...},  # Another relation
            "property_type": "contradictory" | "contrary" | "subcontrary"
        }
        """
        relation_a = input_data.get("relation_a")
        relation_b = input_data.get("relation_b")
        property_type = input_data.get("property_type", "contradictory")

        if not relation_a or not relation_b:
            raise ValueError("Both relation_a and relation_b must be provided")

        result = self.verify_square_property_z3(relation_a, relation_b, property_type)

        return {
            "assertion": f"square_property_{property_type}",
            "result": result.model_dump(),
            "property_type": property_type,
            "relations": [relation_a, relation_b],
        }

    def check_disjointness_z3(
        self, class_a: str, class_b: str, e_relation: Optional[Dict[str, Any]] = None
    ) -> ProofResult:
        """
        Check if two classes are disjoint using Z3.

        We assert that there exists an element that belongs to both classes.
        - If SAT: Classes overlap (counterexample found)
        - If UNSAT: Classes are disjoint (no overlap possible)

        Args:
            class_a: Name of first class
            class_b: Name of second class
            e_relation: Optional E-relation dict that asserts "No class_a are class_b"
                       Should have "subject" and "predicate" matching class_a and class_b

        Returns:
            ProofResult with is_valid=True if disjoint, False if overlap
        """
        start_time = time.time()

        try:
            # Create Z3 solver
            solver = z3.Solver()
            solver.set("timeout", self.timeout)

            # Create uninterpreted sorts for classes
            Element = z3.DeclareSort("Element")

            # Create predicates for class membership
            ClassA = z3.Function(f"is_{class_a}", Element, z3.BoolSort())
            ClassB = z3.Function(f"is_{class_b}", Element, z3.BoolSort())

            # Create an element variable
            x = z3.Const("x", Element)

            # If E-relation is provided and matches, add the constraint
            # E-relation: "No X are Y" means ∀x. X(x) → ¬Y(x)
            if e_relation:
                e_subject = e_relation.get("subject")
                e_predicate = e_relation.get("predicate")
                # Check if the E-relation matches our classes (in either direction)
                if (e_subject == class_a and e_predicate == class_b) or (
                    e_subject == class_b and e_predicate == class_a
                ):
                    # Add E-relation constraint: ∀x. ClassA(x) → ¬ClassB(x)
                    # (or vice versa depending on which is subject/predicate)
                    if e_subject == class_a:
                        solver.add(z3.ForAll([x], z3.Implies(ClassA(x), z3.Not(ClassB(x)))))
                    else:
                        solver.add(z3.ForAll([x], z3.Implies(ClassB(x), z3.Not(ClassA(x)))))

            # Assert that x belongs to both classes (negation of disjointness)
            # We're checking if ∃x. ClassA(x) ∧ ClassB(x) is satisfiable
            solver.add(ClassA(x))
            solver.add(ClassB(x))

            # Check satisfiability
            check_result = solver.check()

            proof_time_ms = int((time.time() - start_time) * 1000)

            if check_result == z3.sat:
                # Classes overlap (not disjoint)
                model = solver.model()
                counterexample = {
                    "result": "overlap_found",
                    "model": str(model),
                    "explanation": f"Found element belonging to both {class_a} and {class_b}",
                }

                return ProofResult(
                    is_valid=False,  # Not disjoint
                    proof_time_ms=proof_time_ms,
                    prover_output=f"SAT: Classes overlap",
                    counterexample=counterexample,
                )
            elif check_result == z3.unsat:
                # Classes are disjoint
                return ProofResult(
                    is_valid=True,  # Disjoint
                    proof_time_ms=proof_time_ms,
                    prover_output=f"UNSAT: Classes are disjoint",
                    counterexample=None,
                )
            else:
                # Unknown (timeout or other issue)
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=proof_time_ms,
                    prover_output=f"UNKNOWN: Solver could not determine result",
                    error_message="Solver returned unknown",
                )

        except Exception as e:
            proof_time_ms = int((time.time() - start_time) * 1000)
            return ProofResult(
                is_valid=False,
                proof_time_ms=proof_time_ms,
                prover_output=None,
                error_message=str(e),
            )

    def check_satisfiability_z3(
        self, formula_desc: str, constraints: list
    ) -> ProofResult:
        """
        Check if a logical formula with constraints is satisfiable.

        Args:
            formula_desc: Description of the formula
            constraints: List of constraint dictionaries

        Returns:
            ProofResult with is_valid=True if satisfiable
        """
        start_time = time.time()

        try:
            solver = z3.Solver()
            solver.set("timeout", self.timeout)

            # Create variables based on constraints
            variables = {}
            for constraint in constraints:
                var_name = constraint.get("variable")
                var_type = constraint.get("type", "Bool")

                if var_name and var_name not in variables:
                    if var_type == "Bool":
                        variables[var_name] = z3.Bool(var_name)
                    elif var_type == "Int":
                        variables[var_name] = z3.Int(var_name)
                    elif var_type == "Real":
                        variables[var_name] = z3.Real(var_name)

            # Add constraints to solver
            for constraint in constraints:
                constraint_type = constraint.get("constraint_type")
                var_name = constraint.get("variable")

                if var_name in variables:
                    var = variables[var_name]

                    if constraint_type == "equals":
                        value = constraint.get("value")
                        if value is not None:
                            solver.add(var == value)
                    elif constraint_type == "not_equals":
                        value = constraint.get("value")
                        if value is not None:
                            solver.add(var != value)
                    elif constraint_type == "implies":
                        var2_name = constraint.get("implies_var")
                        if var2_name in variables:
                            solver.add(z3.Implies(var, variables[var2_name]))

            check_result = solver.check()
            proof_time_ms = int((time.time() - start_time) * 1000)

            if check_result == z3.sat:
                model = solver.model()
                return ProofResult(
                    is_valid=True,
                    proof_time_ms=proof_time_ms,
                    prover_output=f"SAT: Formula is satisfiable - {str(model)}",
                    counterexample=None,
                )
            elif check_result == z3.unsat:
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=proof_time_ms,
                    prover_output="UNSAT: Formula is unsatisfiable",
                    counterexample=None,
                )
            else:
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=proof_time_ms,
                    prover_output="UNKNOWN",
                    error_message="Solver returned unknown",
                )

        except Exception as e:
            proof_time_ms = int((time.time() - start_time) * 1000)
            return ProofResult(
                is_valid=False,
                proof_time_ms=proof_time_ms,
                prover_output=None,
                error_message=str(e),
            )

    def verify_square_property_z3(
        self, relation_a: Dict[str, Any], relation_b: Dict[str, Any], property_type: str
    ) -> ProofResult:
        """
        Verify Square of Opposition properties using Z3.

        Properties:
        - Contradictory (A vs O, E vs I): Cannot both be true or both be false
        - Contrary (A vs E): Cannot both be true (but can both be false)
        - Subcontrary (I vs O): Cannot both be false (but can both be true)

        Args:
            relation_a: First relation (with type, subject, predicate)
            relation_b: Second relation
            property_type: "contradictory", "contrary", or "subcontrary"

        Returns:
            ProofResult indicating if the property holds
        """
        start_time = time.time()

        try:
            solver = z3.Solver()
            solver.set("timeout", self.timeout)

            # Extract relation types
            type_a = relation_a.get("relation_type") or relation_a.get("type")
            type_b = relation_b.get("relation_type") or relation_b.get("type")

            if not type_a or not type_b:
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=0,
                    prover_output=None,
                    error_message="Both relations must have a relation_type or type field",
                )
            subject_a = relation_a.get("subject")
            predicate_a = relation_a.get("predicate")
            subject_b = relation_b.get("subject")
            predicate_b = relation_b.get("predicate")

            # Check if relations are about the same subject and predicate
            if subject_a != subject_b or predicate_a != predicate_b:
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=0,
                    prover_output=None,
                    error_message="Relations must have same subject and predicate",
                )

            # Create domain
            Element = z3.DeclareSort("Element")
            x = z3.Const("x", Element)

            # Create predicates
            S = z3.Function(f"is_{subject_a}", Element, z3.BoolSort())
            P = z3.Function(f"is_{predicate_a}", Element, z3.BoolSort())

            # Create propositions for each relation type
            prop_a = self._create_square_proposition(type_a, S, P, x)
            prop_b = self._create_square_proposition(type_b, S, P, x)

            # Verify the property
            if property_type == "contradictory":
                # Contradictory: ¬(A ∧ B) ∧ ¬(¬A ∧ ¬B)
                # i.e., not both true AND not both false
                # Check if we can have both true or both false
                solver.add(
                    z3.Or(
                        z3.And(prop_a, prop_b),  # Both true
                        z3.And(z3.Not(prop_a), z3.Not(prop_b)),  # Both false
                    )
                )

            elif property_type == "contrary":
                # Contrary: ¬(A ∧ B)
                # Cannot both be true
                solver.add(z3.And(prop_a, prop_b))

            elif property_type == "subcontrary":
                # Subcontrary: A ∨ B
                # Cannot both be false (at least one must be true)
                solver.add(z3.And(z3.Not(prop_a), z3.Not(prop_b)))

            else:
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=0,
                    prover_output=None,
                    error_message=f"Unknown property type: {property_type}",
                )

            check_result = solver.check()
            proof_time_ms = int((time.time() - start_time) * 1000)

            if check_result == z3.sat:
                # Found a counterexample - property is violated
                model = solver.model()
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=proof_time_ms,
                    prover_output=f"Property violated: {property_type}",
                    counterexample={"model": str(model)},
                )
            elif check_result == z3.unsat:
                # No counterexample - property holds
                return ProofResult(
                    is_valid=True,
                    proof_time_ms=proof_time_ms,
                    prover_output=f"Property verified: {property_type}",
                    counterexample=None,
                )
            else:
                return ProofResult(
                    is_valid=False,
                    proof_time_ms=proof_time_ms,
                    prover_output="UNKNOWN",
                    error_message="Solver returned unknown",
                )

        except Exception as e:
            proof_time_ms = int((time.time() - start_time) * 1000)
            return ProofResult(
                is_valid=False,
                proof_time_ms=proof_time_ms,
                prover_output=None,
                error_message=str(e),
            )

    def _create_square_proposition(self, relation_type: str, S, P, x):
        """
        Create Z3 proposition based on Square of Opposition relation type.

        A (universal affirmative): ∀x. S(x) → P(x)
        E (universal negative): ∀x. S(x) → ¬P(x)
        I (particular affirmative): ∃x. S(x) ∧ P(x)
        O (particular negative): ∃x. S(x) ∧ ¬P(x)
        """
        # For universal quantifiers, we use ForAll
        # For particular quantifiers, we use Exists

        if relation_type in ["A", "universal_affirmative", LogicRelationType.A]:
            # All S are P: ∀x. S(x) → P(x)
            return z3.ForAll([x], z3.Implies(S(x), P(x)))

        elif relation_type in ["E", "universal_negative", LogicRelationType.E]:
            # No S are P: ∀x. S(x) → ¬P(x)
            return z3.ForAll([x], z3.Implies(S(x), z3.Not(P(x))))

        elif relation_type in ["I", "particular_affirmative", LogicRelationType.I]:
            # Some S are P: ∃x. S(x) ∧ P(x)
            return z3.Exists([x], z3.And(S(x), P(x)))

        elif relation_type in ["O", "particular_negative", LogicRelationType.O]:
            # Some S are not P: ∃x. S(x) ∧ ¬P(x)
            return z3.Exists([x], z3.And(S(x), z3.Not(P(x))))

        else:
            raise ValueError(f"Unknown relation type: {relation_type}")
