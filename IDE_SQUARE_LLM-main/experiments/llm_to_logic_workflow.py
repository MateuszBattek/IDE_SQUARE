import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent


async def example_workflow():
    print("=" * 80)
    print("EXAMPLE: LLMAgent → LogicAgent Workflow")
    print("=" * 80)
    
    user_input = """
    Order management system:
    - All new orders are in pending state
    - No order in cancelled state is in processing state
    - Some orders are priority
    - Not all pending orders are priority
    - Order can transition from pending to processing
    - Order can transition from processing to completed
    - Order can be cancelled from any state
    """
    
    print("\n📝 USER INPUT:")
    print(user_input)
    
    print("\n" + "=" * 80)
    print("STEP 1: LLMAgent extracts requirements")
    print("=" * 80)
    
    llm_agent = LLMAgent()
    
    llm_input = {
        "task_type": "extract_requirements",
        "user_input": user_input
    }
    
    print("\n🤖 LLMAgent processing input...")
    llm_result = await llm_agent.execute(llm_input)
    
    if not llm_result["success"]:
        print(f"❌ LLMAgent error: {llm_result['error_message']}")
        return
    
    requirements = llm_result["result"]["requirements"]
    confidence = llm_result["result"]["confidence"]
    needs_clarification = llm_result["result"]["needs_clarification"]
    
    print(f"\n✅ LLMAgent completed (time: {llm_result['processing_time_ms']}ms)")
    print(f"📊 Confidence: {confidence}")
    print(f"⚠️  Needs clarification: {needs_clarification}")
    
    print("\n📋 EXTRACTED FORMULAS:")
    formulas = requirements.get("formulas", [])
    for i, formula in enumerate(formulas, 1):
        print(f"\n  {i}. Type: {formula['type']}")
        print(f"     Subject: {formula['subject']}")
        print(f"     Predicate: {formula['predicate']}")
        print(f"     Source: {formula.get('source_text', 'N/A')}")
        print(f"     Confidence: {formula.get('confidence', 'N/A')}")
    
    print("\n🎯 IDENTIFIED ENTITIES:")
    entities = requirements.get("entities", [])
    print(f"  {', '.join(entities) if entities else 'None'}")
    
    print("\n🔄 STATES:")
    states = requirements.get("states", [])
    print(f"  {', '.join(states) if states else 'None'}")
    
    print("\n➡️  TRANSITIONS:")
    transitions = requirements.get("transitions", [])
    for trans in transitions:
        condition = f" [{trans.get('condition')}]" if trans.get('condition') else ""
        print(f"  {trans.get('from')} → {trans.get('to')}{condition}")
    
    ambiguities = requirements.get("ambiguities", [])
    if ambiguities:
        print("\n⚠️  AMBIGUITIES:")
        for amb in ambiguities:
            print(f"  - {amb}")
    
    print("\n" + "=" * 80)
    print("STEP 2: LogicAgent processes requirements")
    print("=" * 80)
    
    logic_agent = LogicAgent()
    
    logic_input = {
        "requirements": requirements
    }
    
    print("\n🧠 LogicAgent verifying and building logic model...")
    logic_result = await logic_agent.execute(logic_input)
    
    if not logic_result["success"]:
        print(f"❌ LogicAgent error: {logic_result['error_message']}")
        return
    
    print(f"\n✅ LogicAgent completed (time: {logic_result['processing_time_ms']}ms)")
    
    result_data = logic_result["result"]
    
    print(f"\n📊 LOGIC MODEL STATISTICS:")
    print(f"  Number of relations: {result_data['relations_count']}")
    print(f"  Number of entities: {len(result_data['entities_found'])}")
    print(f"  Consistency: {'✅ YES' if result_data['is_consistent'] else '❌ NO'}")
    
    logic_model = result_data["logic_model"]
    
    print("\n🔍 LOGICAL RELATIONS (Square of Opposition):")
    relations = logic_model.get("relations", [])
    
    by_type = {}
    for rel in relations:
        rel_type = rel["relation_type"]
        if rel_type not in by_type:
            by_type[rel_type] = []
        by_type[rel_type].append(rel)
    
    type_names = {
        "universal_affirmative": "A - All X are Y",
        "universal_negative": "E - No X are Y",
        "particular_affirmative": "I - Some X are Y",
        "particular_negative": "O - Some X are not Y"
    }
    
    for rel_type, rels in by_type.items():
        print(f"\n  {type_names.get(rel_type, rel_type)}:")
        for rel in rels:
            conf = rel.get('confidence', 1.0)
            print(f"    • {rel['subject']} → {rel['predicate']} (confidence: {conf:.2f})")
    
    contradictions = result_data.get("contradictions", [])
    if contradictions:
        print("\n⚠️  DETECTED CONTRADICTIONS:")
        for contr in contradictions:
            print(f"\n  Type: {contr['type']}")
            print(f"  Description: {contr['description']}")
    else:
        print("\n✅ No contradictions in logic model")
    
    state_model = result_data.get("state_model")
    if state_model:
        print("\n🔄 PRELIMINARY STATE MODEL:")
        states = state_model.get("states", [])
        print(f"\n  States ({len(states)}):")
        for state in states:
            initial = " [INITIAL]" if state.get("is_initial") else ""
            final = " [FINAL]" if state.get("is_final") else ""
            print(f"    • {state['name']}{initial}{final}")
            
            props = state.get("properties", {})
            if props:
                print(f"      Properties: {props}")
        
        transitions = state_model.get("transitions", [])
        if transitions:
            print(f"\n  Transitions ({len(transitions)}):")
            for trans in transitions:
                condition = f" [condition: {trans.get('condition')}]" if trans.get('condition') else ""
                print(f"    • {trans['from_state']} → {trans['to_state']}{condition}")
        
        metadata = state_model.get("metadata", {})
        if metadata.get("inferred"):
            print("\n  ℹ️  Some states were automatically inferred from logical relations")
    
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"""
    1. ✅ LLMAgent translated natural language to structured requirements
       - Extracted {len(formulas)} logical formulas
       - Identified {len(entities)} entities
       - Found {len(transitions)} state transitions
    
    2. ✅ LogicAgent verified and processed requirements
       - Created {result_data['relations_count']} logical relations
       - Checked Square of Opposition consistency
       - Built preliminary state model
    
    3. 🎯 Result ready to pass to StateAgent for further elaboration
    """)


async def example_simple():
    print("\n" + "=" * 80)
    print("SIMPLE EXAMPLE: E-commerce business logic")
    print("=" * 80)
    
    user_input = """
    All premium products have free shipping.
    No damaged product is available for sale.
    Some products are on promotion.
    """
    
    print(f"\n📝 INPUT: {user_input}")
    
    llm_agent = LLMAgent()
    logic_agent = LogicAgent()
    
    print("\n⏳ LLMAgent extracting requirements...")
    llm_result = await llm_agent.execute({
        "task_type": "extract_requirements",
        "user_input": user_input
    })
    
    if llm_result["success"]:
        requirements = llm_result["result"]["requirements"]
        print(f"✅ Extracted {len(requirements.get('formulas', []))} formulas")
        
        print("\n⏳ LogicAgent processing requirements...")
        logic_result = await logic_agent.execute({"requirements": requirements})
        
        if logic_result["success"]:
            relations_count = logic_result["result"]["relations_count"]
            is_consistent = logic_result["result"]["is_consistent"]
            print(f"✅ Created {relations_count} logical relations")
            print(f"{'✅' if is_consistent else '❌'} Model {'consistent' if is_consistent else 'inconsistent'}")
        else:
            print(f"❌ Error: {logic_result['error_message']}")
    else:
        print(f"❌ Error: {llm_result['error_message']}")


async def example_with_contradictions():
    print("\n" + "=" * 80)
    print("EXAMPLE WITH CONTRADICTIONS")
    print("=" * 80)
    
    user_input = """
    All documents are approved.
    No documents are approved.
    Some documents require signature.
    """
    
    print(f"\n📝 INPUT (contains contradictions): {user_input}")
    
    llm_agent = LLMAgent()
    logic_agent = LogicAgent()
    
    print("\n⏳ Processing...")
    llm_result = await llm_agent.execute({
        "task_type": "extract_requirements",
        "user_input": user_input
    })
    
    if llm_result["success"]:
        requirements = llm_result["result"]["requirements"]
        logic_result = await logic_agent.execute({"requirements": requirements})
        
        if logic_result["success"]:
            contradictions = logic_result["result"]["contradictions"]
            if contradictions:
                print(f"\n⚠️  DETECTED {len(contradictions)} CONTRADICTIONS:")
                for contr in contradictions:
                    print(f"\n  {contr['type']}:")
                    print(f"  {contr['description']}")
            else:
                print("\n✅ No contradictions")


async def main():
    print("\n🚀 DEMONSTRATION: LLMAgent → LogicAgent Workflow\n")
    
    await example_workflow()
    
    print("\n\n")
    await example_simple()
    
    print("\n\n")
    await example_with_contradictions()
    
    print("\n\n✅ All examples completed!\n")


if __name__ == "__main__":
    asyncio.run(main())

