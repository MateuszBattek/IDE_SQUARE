import asyncio
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agent import LLMAgent
from src.agents.logic_agent import LogicAgent


async def run_workflow(user_input: str):
    llm_agent = LLMAgent()
    logic_agent = LogicAgent()
    
    llm_result = await llm_agent.execute({
        "task_type": "extract_requirements",
        "user_input": user_input
    })
    
    if not llm_result["success"]:
        print(f"LLMAgent error: {llm_result['error_message']}")
        return None
    
    requirements = llm_result["result"]["requirements"]
    
    logic_result = await logic_agent.execute({
        "requirements": requirements
    })
    
    if not logic_result["success"]:
        print(f"LogicAgent error: {logic_result['error_message']}")
        return None
    
    return {
        "llm_result": llm_result,
        "logic_result": logic_result,
        "requirements": requirements
    }


async def main():
    user_input = """
    Hotel reservation system:
    - All premium rooms have a balcony
    - No occupied room is available for reservation
    - Some rooms have an ocean view
    - Not all rooms are air-conditioned
    
    A room can transition from available to reserved.
    A room can transition from reserved to occupied.
    """
    
    print("=" * 60)
    print("USER INPUT:")
    print("=" * 60)
    print(user_input)
    
    print("\n" + "=" * 60)
    print("PROCESSING...")
    print("=" * 60)
    
    result = await run_workflow(user_input)
    
    if result:
        requirements = result["requirements"]
        logic_result = result["logic_result"]["result"]
        
        print("\n✅ EXTRACTED FORMULAS:")
        for formula in requirements.get("formulas", []):
            print(f"  [{formula['type']}] {formula['subject']} → {formula['predicate']}")
        
        print(f"\n✅ LOGIC MODEL:")
        print(f"  Relations: {logic_result['relations_count']}")
        print(f"  Entities: {len(logic_result['entities_found'])}")
        print(f"  Consistent: {logic_result['is_consistent']}")
        
        if logic_result.get('state_model'):
            state_model = logic_result['state_model']
            print(f"\n✅ STATE MODEL:")
            print(f"  States: {len(state_model['states'])}")
            print(f"  Transitions: {len(state_model['transitions'])}")
        
        if logic_result.get('contradictions'):
            print(f"\n⚠️  CONTRADICTIONS FOUND:")
            for contr in logic_result['contradictions']:
                print(f"  - {contr['description']}")
        
        print("\n" + "=" * 60)
        print("REQUIREMENTS (JSON):")
        print("=" * 60)
        print(json.dumps(requirements, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

