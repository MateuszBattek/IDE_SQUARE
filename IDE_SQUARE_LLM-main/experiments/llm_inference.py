from src.agents.llm_agent import LLMAgent
import json
import asyncio


async def run_demo_case(title: str, relation_type: str, subject: str, predicate: str):
    """Helper for readable and consistent demo output."""
    agent = LLMAgent()

    payload = {
        "task_type": "infer_logic_square",
        "relation": {
            "type": relation_type,
            "subject": subject,
            "predicate": predicate
        }
    }

    print(f"\n=== {title} ===")
    result = await agent.process(payload)

    print(json.dumps(result, indent=4, ensure_ascii=False))


async def main():
    # -----------------------------------------
    # DEMO 1 — A (Universal Affirmative, True)
    # “All cars are red” is TRUE
    # -----------------------------------------
    await run_demo_case(
        title="DEMO 1: Inference for A (Universal Affirmative, True).\n All cars are red. Based on this information, we can infer the following:",
        relation_type="universal_affirmative",
        subject="cars",
        predicate="red"
    )

    # -----------------------------------------
    # DEMO 2 — O (Particular Negative, True)
    # “Some birds do not fly” is TRUE
    # -----------------------------------------
    await run_demo_case(
        title="DEMO 2: Inference for O (Particular Negative, True).\nSome birds do not fly. Based on this information, we can infer the following:",
        relation_type="particular_negative",
        subject="birds",
        predicate="fly"
    )

    # -----------------------------------------
    # DEMO 3 — I (Particular Affirmative, True) 
    # “Some fully autonomous electric vehicles are highway-certified” is TRUE
    await run_demo_case(
        title="DEMO 3: Inference for I (Particular Affirmative, True). \nSome fully autonomous electric vehicles are highway-certified. Based on this information, we can infer the following:",
        relation_type="particular_affirmative",
        subject="fully autonomous electric vehicles",
        predicate="highway-certified"
    )

    await run_demo_case(
        title="DEMO 4: Inference for E (Universal Negative, True). \nNo reptiles are mammals. Based on this information, we can infer the following:",
        relation_type="universal_negative",
        subject="reptiles",
        predicate="mammals"
    )


if __name__ == "__main__":
    asyncio.run(main())
