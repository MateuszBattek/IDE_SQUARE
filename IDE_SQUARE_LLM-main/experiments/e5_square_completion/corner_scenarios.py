"""
Corner scenarios for E5 Square Completion experiment.

Provides test cases with 1, 2, or 3 corners of the Square of Opposition
to test inference accuracy.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .models import CornerType, SquareRelation


@dataclass
class SquareTestCase:
    """A complete Square of Opposition test case."""
    name: str
    subject: str
    predicate: str
    
    # Full square relations (ground truth)
    a_status: str  # TRUE, FALSE, UNDETERMINED
    e_status: str
    i_status: str
    o_status: str
    
    # Natural language description
    domain: str = ""
    
    def get_relation(self, corner: CornerType) -> SquareRelation:
        """Get relation for a specific corner."""
        status_map = {
            CornerType.A: self.a_status,
            CornerType.E: self.e_status,
            CornerType.I: self.i_status,
            CornerType.O: self.o_status,
        }
        
        statement_map = {
            CornerType.A: f"All {self.subject} are {self.predicate}.",
            CornerType.E: f"No {self.subject} are {self.predicate}.",
            CornerType.I: f"Some {self.subject} are {self.predicate}.",
            CornerType.O: f"Some {self.subject} are not {self.predicate}.",
        }
        
        return SquareRelation(
            corner=corner,
            subject=self.subject,
            predicate=self.predicate,
            status=status_map[corner],
            statement=statement_map[corner],
        )
    
    def get_all_relations(self) -> Dict[CornerType, SquareRelation]:
        """Get all four relations."""
        return {ct: self.get_relation(ct) for ct in CornerType}


# ============================================================================
# Pre-defined test cases based on Square of Opposition logic
# ============================================================================

SQUARE_TEST_CASES = [
    # Case 1: A is TRUE -> E is FALSE, I is TRUE, O is FALSE
    SquareTestCase(
        name="order_complete",
        subject="completed_order",
        predicate="processed",
        a_status="TRUE",
        e_status="FALSE",
        i_status="TRUE",
        o_status="FALSE",
        domain="e-commerce",
    ),
    
    # Case 2: E is TRUE -> A is FALSE, I is FALSE, O is TRUE
    SquareTestCase(
        name="cancelled_not_active",
        subject="cancelled_order",
        predicate="active",
        a_status="FALSE",
        e_status="TRUE",
        i_status="FALSE",
        o_status="TRUE",
        domain="e-commerce",
    ),
    
    # Case 3: I is TRUE -> A is UNDETERMINED, E is FALSE, O is UNDETERMINED
    SquareTestCase(
        name="some_priority",
        subject="order",
        predicate="priority",
        a_status="UNDETERMINED",
        e_status="FALSE",
        i_status="TRUE",
        o_status="UNDETERMINED",
        domain="e-commerce",
    ),
    
    # Case 4: O is TRUE -> A is FALSE, E is UNDETERMINED, I is UNDETERMINED
    SquareTestCase(
        name="not_all_shipped",
        subject="order",
        predicate="shipped",
        a_status="FALSE",
        e_status="UNDETERMINED",
        i_status="UNDETERMINED",
        o_status="TRUE",
        domain="logistics",
    ),
    
    # Case 5: A is TRUE (user account domain)
    SquareTestCase(
        name="active_verified",
        subject="active_account",
        predicate="verified",
        a_status="TRUE",
        e_status="FALSE",
        i_status="TRUE",
        o_status="FALSE",
        domain="identity",
    ),
    
    # Case 6: E is TRUE (document workflow)
    SquareTestCase(
        name="rejected_not_approved",
        subject="rejected_document",
        predicate="approved",
        a_status="FALSE",
        e_status="TRUE",
        i_status="FALSE",
        o_status="TRUE",
        domain="enterprise",
    ),
]


class OneCornerScenario:
    """
    C1: One corner given, infer remaining three.
    
    Tests: A->EIO, E->AIO, I->AEO, O->AEI
    """
    
    @staticmethod
    def generate_cases(test_case: SquareTestCase) -> List[Dict[str, Any]]:
        """Generate all 4 one-corner scenarios for a test case."""
        cases = []
        
        for given_corner in CornerType:
            given_relation = test_case.get_relation(given_corner)
            
            # Expected inferences (the other 3 corners)
            expected = {}
            for corner in CornerType:
                if corner != given_corner:
                    expected[corner.value] = test_case.get_relation(corner)
            
            cases.append({
                "test_case_name": f"{test_case.name}_from_{given_corner.name}",
                "given_corners": [given_corner],
                "given_relations": [given_relation],
                "expected_inferences": expected,
                "subject": test_case.subject,
                "predicate": test_case.predicate,
            })
        
        return cases


class TwoCornerScenario:
    """
    C2: Two corners given, infer remaining two.
    
    Key pairs: A+E (contraries), I+O (subcontraries), A+O (contradictories), E+I (contradictories)
    """
    
    # Interesting two-corner combinations
    PAIRS = [
        (CornerType.A, CornerType.E),  # Contraries
        (CornerType.I, CornerType.O),  # Subcontraries
        (CornerType.A, CornerType.O),  # Contradictories
        (CornerType.E, CornerType.I),  # Contradictories
        (CornerType.A, CornerType.I),  # Subalterns
        (CornerType.E, CornerType.O),  # Subalterns
    ]
    
    @staticmethod
    def generate_cases(test_case: SquareTestCase) -> List[Dict[str, Any]]:
        """Generate two-corner scenarios for a test case."""
        cases = []
        
        for corner1, corner2 in TwoCornerScenario.PAIRS:
            rel1 = test_case.get_relation(corner1)
            rel2 = test_case.get_relation(corner2)
            
            # Expected inferences (the other 2 corners)
            expected = {}
            for corner in CornerType:
                if corner not in (corner1, corner2):
                    expected[corner.value] = test_case.get_relation(corner)
            
            cases.append({
                "test_case_name": f"{test_case.name}_from_{corner1.name}_{corner2.name}",
                "given_corners": [corner1, corner2],
                "given_relations": [rel1, rel2],
                "expected_inferences": expected,
                "subject": test_case.subject,
                "predicate": test_case.predicate,
            })
        
        return cases


class ThreeCornerScenario:
    """
    C3: Three corners given, infer remaining one.
    
    Should have highest accuracy - only one corner to infer.
    """
    
    @staticmethod
    def generate_cases(test_case: SquareTestCase) -> List[Dict[str, Any]]:
        """Generate all 4 three-corner scenarios for a test case."""
        cases = []
        
        for missing_corner in CornerType:
            given_corners = [c for c in CornerType if c != missing_corner]
            given_relations = [test_case.get_relation(c) for c in given_corners]
            
            # Expected inference (the missing corner)
            expected = {
                missing_corner.value: test_case.get_relation(missing_corner)
            }
            
            cases.append({
                "test_case_name": f"{test_case.name}_infer_{missing_corner.name}",
                "given_corners": given_corners,
                "given_relations": given_relations,
                "expected_inferences": expected,
                "subject": test_case.subject,
                "predicate": test_case.predicate,
            })
        
        return cases


def generate_all_test_cases() -> Dict[str, List[Dict[str, Any]]]:
    """Generate all test cases for all scenarios."""
    all_cases = {
        "C1_one_corner": [],
        "C2_two_corners": [],
        "C3_three_corners": [],
    }
    
    for test_case in SQUARE_TEST_CASES:
        all_cases["C1_one_corner"].extend(OneCornerScenario.generate_cases(test_case))
        all_cases["C2_two_corners"].extend(TwoCornerScenario.generate_cases(test_case))
        all_cases["C3_three_corners"].extend(ThreeCornerScenario.generate_cases(test_case))
    
    return all_cases
