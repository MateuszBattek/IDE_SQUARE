import asyncio
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.logic_agent import LogicAgent


async def example_basic():
    print("=" * 80)
    print("EXAMPLE 1: Basic Logic Agent Processing")
    print("=" * 80)
    
    requirements = {
        "formulas": [
            {
                "type": "universal_affirmative",
                "subject": "premium_users",
                "predicate": "verified",
                "source_text": "All premium users are verified",
                "confidence": 0.95
            },
            {
                "type": "universal_negative",
                "subject": "banned_users",
                "predicate": "active",
                "source_text": "No banned users are active",
                "confidence": 0.98
            },
            {
                "type": "particular_affirmative",
                "subject": "users",
                "predicate": "premium",
                "source_text": "Some users are premium",
                "confidence": 0.90
            }
        ],
        "entities": ["users", "premium_users", "banned_users", "verified", "active"],
        "states": ["active", "banned", "pending"],
        "transitions": [
            {"from": "pending", "to": "active", "condition": "verification_complete"},
            {"from": "active", "to": "banned", "condition": "violation_detected"}
        ],
        "ambiguities": [],
        "overall_confidence": 0.92
    }
    
    print("\n📋 INPUT REQUIREMENTS:")
    print(json.dumps(requirements, indent=2))
    
    logic_agent = LogicAgent()
    
    print("\n🧠 LogicAgent processing...")
    result = await logic_agent.execute({"requirements": requirements})
    
    if result["success"]:
        print(f"\n✅ Processing completed in {result['processing_time_ms']}ms")
        
        result_data = result["result"]
        
        print(f"\n📊 RESULTS:")
        print(f"  Relations created: {result_data['relations_count']}")
        print(f"  Entities found: {len(result_data['entities_found'])}")
        print(f"  Is consistent: {result_data['is_consistent']}")
        
        print("\n🔍 LOGICAL RELATIONS:")
        logic_model = result_data["logic_model"]
        for relation in logic_model["relations"]:
            print(f"  [{relation['relation_type']}] {relation['subject']} → {relation['predicate']} (confidence: {relation['confidence']})")
        
        if result_data.get("contradictions"):
            print("\n⚠️  CONTRADICTIONS:")
            for contr in result_data["contradictions"]:
                print(f"  - {contr['description']}")
        else:
            print("\n✅ No contradictions detected")
        
        if result_data.get("state_model"):
            state_model = result_data["state_model"]
            print("\n🔄 STATE MODEL:")
            print(f"  States: {len(state_model['states'])}")
            for state in state_model['states']:
                initial = " [INITIAL]" if state.get("is_initial") else ""
                print(f"    • {state['name']}{initial}")
            
            print(f"  Transitions: {len(state_model['transitions'])}")
            for trans in state_model['transitions']:
                condition = f" [when: {trans.get('condition')}]" if trans.get('condition') else ""
                print(f"    • {trans['from_state']} → {trans['to_state']}{condition}")
    else:
        print(f"\n❌ Error: {result['error_message']}")


async def example_with_contradictions():
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Logic Agent with Contradictions")
    print("=" * 80)
    
    requirements = {
        "formulas": [
            {
                "type": "universal_affirmative",
                "subject": "documents",
                "predicate": "approved",
                "source_text": "All documents are approved",
                "confidence": 0.85
            },
            {
                "type": "universal_negative",
                "subject": "documents",
                "predicate": "approved",
                "source_text": "No documents are approved",
                "confidence": 0.80
            },
            {
                "type": "particular_affirmative",
                "subject": "documents",
                "predicate": "signed",
                "source_text": "Some documents are signed",
                "confidence": 0.90
            }
        ],
        "entities": ["documents", "approved", "signed"],
        "states": [],
        "transitions": [],
        "ambiguities": ["Conflicting statements about document approval"],
        "overall_confidence": 0.65
    }
    
    print("\n📋 INPUT REQUIREMENTS (with contradictions):")
    print(json.dumps(requirements, indent=2))
    
    logic_agent = LogicAgent()
    
    print("\n🧠 LogicAgent processing...")
    result = await logic_agent.execute({"requirements": requirements})
    
    if result["success"]:
        result_data = result["result"]
        
        print(f"\n📊 RESULTS:")
        print(f"  Relations created: {result_data['relations_count']}")
        print(f"  Is consistent: {result_data['is_consistent']}")
        
        if result_data.get("contradictions"):
            print(f"\n⚠️  DETECTED {len(result_data['contradictions'])} CONTRADICTIONS:")
            for i, contr in enumerate(result_data["contradictions"], 1):
                print(f"\n  {i}. Type: {contr['type']}")
                print(f"     Description: {contr['description']}")
                print(f"     Relations involved: {contr['relations']}")


async def example_order_system():
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Order Management System")
    print("=" * 80)
    
    requirements = {
        "formulas": [
            {
                "type": "universal_affirmative",
                "subject": "new_orders",
                "predicate": "pending",
                "source_text": "All new orders are pending",
                "confidence": 1.0
            },
            {
                "type": "universal_negative",
                "subject": "cancelled_orders",
                "predicate": "processing",
                "source_text": "No cancelled orders are processing",
                "confidence": 0.95
            },
            {
                "type": "particular_affirmative",
                "subject": "orders",
                "predicate": "priority",
                "source_text": "Some orders are priority",
                "confidence": 0.88
            },
            {
                "type": "particular_negative",
                "subject": "pending_orders",
                "predicate": "priority",
                "source_text": "Not all pending orders are priority",
                "confidence": 0.92
            }
        ],
        "entities": ["orders", "new_orders", "pending_orders", "cancelled_orders", 
                     "pending", "processing", "priority", "completed"],
        "states": ["pending", "processing", "completed", "cancelled"],
        "transitions": [
            {"from": "pending", "to": "processing", "condition": "payment_confirmed"},
            {"from": "processing", "to": "completed", "condition": "shipped"},
            {"from": "pending", "to": "cancelled", "condition": "user_cancelled"},
            {"from": "processing", "to": "cancelled", "condition": "payment_failed"}
        ],
        "ambiguities": [],
        "overall_confidence": 0.93
    }
    
    print("\n📋 INPUT REQUIREMENTS:")
    for i, formula in enumerate(requirements["formulas"], 1):
        print(f"  {i}. [{formula['type']}] {formula['subject']} → {formula['predicate']}")
    
    logic_agent = LogicAgent()
    
    print("\n🧠 LogicAgent processing...")
    result = await logic_agent.execute({"requirements": requirements})
    
    if result["success"]:
        result_data = result["result"]
        
        print(f"\n✅ Processing completed")
        print(f"\n📊 LOGIC MODEL STATISTICS:")
        print(f"  Relations: {result_data['relations_count']}")
        print(f"  Entities: {len(result_data['entities_found'])}")
        print(f"  Consistent: {result_data['is_consistent']}")
        
        print("\n🔍 RELATIONS BY TYPE:")
        logic_model = result_data["logic_model"]
        relations_by_type = {}
        for rel in logic_model["relations"]:
            rel_type = rel["relation_type"]
            if rel_type not in relations_by_type:
                relations_by_type[rel_type] = []
            relations_by_type[rel_type].append(rel)
        
        type_labels = {
            "universal_affirmative": "A (All X are Y)",
            "universal_negative": "E (No X are Y)",
            "particular_affirmative": "I (Some X are Y)",
            "particular_negative": "O (Some X are not Y)"
        }
        
        for rel_type, rels in relations_by_type.items():
            print(f"\n  {type_labels.get(rel_type, rel_type)}:")
            for rel in rels:
                print(f"    • {rel['subject']} → {rel['predicate']}")
        
        if result_data.get("state_model"):
            state_model = result_data["state_model"]
            print(f"\n🔄 PRELIMINARY STATE MODEL:")
            print(f"  States ({len(state_model['states'])}):")
            for state in state_model["states"]:
                props = state.get("properties", {})
                props_str = f" {props}" if props else ""
                print(f"    • {state['name']}{props_str}")
            
            print(f"\n  Transitions ({len(state_model['transitions'])}):")
            for trans in state_model["transitions"]:
                condition = trans.get("condition", "")
                cond_str = f" [when: {condition}]" if condition else ""
                print(f"    • {trans['from_state']} → {trans['to_state']}{cond_str}")


async def example_invalid_formula():
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Invalid Formula Handling")
    print("=" * 80)
    
    requirements = {
        "formulas": [
            {
                "type": "universal_affirmative",
                "subject": "valid_entity",
                "predicate": "valid_property",
                "source_text": "All valid entities have valid property",
                "confidence": 0.95
            },
            {
                "type": "invalid_type",
                "subject": "entity",
                "predicate": "property",
                "source_text": "Invalid formula type",
                "confidence": 0.5
            },
            {
                "type": "universal_negative",
                "subject": "",
                "predicate": "property",
                "source_text": "Empty subject",
                "confidence": 0.8
            }
        ],
        "entities": ["valid_entity", "valid_property"],
        "states": [],
        "transitions": [],
        "ambiguities": [],
        "overall_confidence": 0.7
    }
    
    print("\n📋 INPUT REQUIREMENTS (with invalid formulas):")
    for i, formula in enumerate(requirements["formulas"], 1):
        print(f"  {i}. type={formula.get('type')}, subject={formula.get('subject')}, predicate={formula.get('predicate')}")
    
    logic_agent = LogicAgent()
    
    print("\n🧠 LogicAgent processing...")
    result = await logic_agent.execute({"requirements": requirements})
    
    if result["success"]:
        result_data = result["result"]
        
        print(f"\n✅ Processing completed")
        print(f"\n📊 RESULTS:")
        print(f"  Valid relations created: {result_data['relations_count']}")
        print(f"  Invalid formulas skipped: {len(requirements['formulas']) - result_data['relations_count']}")
        
        print("\n✅ LogicAgent successfully filtered out invalid formulas:")
        logic_model = result_data["logic_model"]
        for rel in logic_model["relations"]:
            print(f"  • [{rel['relation_type']}] {rel['subject']} → {rel['predicate']}")


async def main():
    print("\n🚀 LOGIC AGENT EXAMPLES\n")
    
    await example_basic()
    await example_with_contradictions()
    await example_order_system()
    await example_invalid_formula()
    
    print("\n\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("  1. ✅ Formula verification and validation")
    print("  2. ✅ Logic model construction (Square of Opposition)")
    print("  3. ✅ Contradiction detection (A-E, A-O, E-I)")
    print("  4. ✅ Preliminary state model creation")
    print("  5. ✅ Invalid formula filtering")
    print("  6. ✅ Entity extraction and management")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())

