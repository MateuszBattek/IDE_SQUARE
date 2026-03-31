from ast import Dict
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.llm_agent import LLMAgent


# Text to copy
# All flights are monitored by the tower. No maintenance personnel are allowed on the runway during active takeoff. Some security checks are mandatory. Not all baggage handlers are certified for hazardous materials. Every passenger is safe.

async def run_llm_agent():
    agent = LLMAgent()
    print("\n" + "="*70)

    while True:
        requirements_text = input("\nInput requirements text (or type 'exit' to quit): ")
        
        if requirements_text.lower() in ('exit', 'quit'):
            print("\nStoping the interactive LLM test.")
            break
            
        if not requirements_text:
            continue

        input_data: Dict[str, Any] = {
            "task_type": "extract_requirements",
            "user_input": requirements_text
        }
        
        try:
            result = await agent.process(input_data)
            
            print("\n" + "-"*50)
            print("Result:")
            print("-" * 50)
            
            requirements = result.get('requirements', {})
            
            print(f"Need of clarification: {result.get('needs_clarification')}")
            print(f"Confidence: {result.get('confidence'):.2f}")
            print("-" * 50)
            
            print(json.dumps(requirements, indent=4))
            
            # Display formulas in a readable format
            formulas = requirements.get('formulas', [])
            if formulas:
                print("\n" + "="*50)
                print("EXTRACTED FORMULAS:")
                print("="*50)
                for i, formula in enumerate(formulas, 1):
                    print(f"\n{i}. Type: {formula['type']}")
                    print(f"   Subject: {formula['subject']}")
                    print(f"   Predicate: {formula['predicate']}")
                    print(f"   Source: {formula.get('source_text', 'N/A')}")
                    print(f"   Confidence: {formula.get('confidence', 'N/A')}")
            
            # Display entities
            entities = requirements.get('entities', [])
            if entities:
                print(f"\n{'='*50}")
                print(f"ENTITIES: {', '.join(entities)}")
            
            # Display ambiguities
            ambiguities = requirements.get('ambiguities', [])
            if ambiguities:
                print(f"\n{'='*50}")
                print("AMBIGUITIES:")
                for amb in ambiguities:
                    print(f"  - {amb}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_llm_agent())