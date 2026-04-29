import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from ..agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_OPERATIONS = """\
add_square(a, e, i, o, parent_id?)
  Add a logical square. a/e/i/o are assertion strings; use "true" to skip a corner.
  parent_id: REQUIRED when the FSM already has states — must be one of the IDs from
  the "States eligible for expansion" list. Omit only when the project is empty.
  Constraint: a != o AND e != i (these are opposites in the Square of Opposition).
  All four values (a, e, i, o) MUST describe only the NEW square's own domain —
  never copy or reference the parent state's assertion.

assign_name(state_id, name)
  Assign a human-readable label to a state by its ID.

add_transition(from_state, to_state, event)
  Add a labelled transition between two existing states.

check_states(states)
  Verify logical disjointness. states: list of condition strings,
  e.g. ["flying=true, grounded=false", "grounded=true, flying=false"].

generate_code(format)
  Generate source code. format must be exactly one of: "class", "transition", "qt".

analyze_reachability()
  Find pairs of states where one is not reachable from the other.

reset()
  Reset the entire project to its initial empty state.\
"""


class BotAgent(BaseAgent):
    """Classifies a natural-language command into a single IDE operation with parameters."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("BotAgent", config)
        self._llm = None

    @property
    def _llm_agent(self):
        if self._llm is None:
            from .llm_agent import LLMAgent
            self._llm = LLMAgent()
        return self._llm

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data.get("message", "")
        fsm_context = input_data.get("fsm_context", {})

        states_text = "\n".join(
            f"  id={s['id']}  name={s.get('name', s['id'])}  assertion={s.get('assertion', '')}"
            for s in fsm_context.get("states", [])
        ) or "  (none — project is empty)"

        transitions_text = "\n".join(
            f"  {t['from']} → {t['to']}  event: {t['event']}"
            for t in fsm_context.get("transitions", [])
        ) or "  (none)"

        latest_text = ", ".join(fsm_context.get("latest_states", [])) or "(none)"

        prompt = f"""\
You are an IDE Bot for a Logical Square FSM tool.
Given the user command and the current FSM state, identify the single operation to perform and extract its parameters.

AVAILABLE OPERATIONS:
{_OPERATIONS}

CURRENT FSM STATE:
States:
{states_text}

Transitions:
{transitions_text}

States eligible for expansion (latest): {latest_text}

USER COMMAND:
"{message}"

Respond ONLY with a valid JSON object — no markdown, no extra text:
{{
  "operation": "<operation_name>",
  "params": {{ ... }},
  "message": "<short natural-language confirmation of what you will do>"
}}

Rules:
- Reference states by their exact IDs shown above.
- If the command is ambiguous or unsupported, use operation "unknown" and explain in message.
- For add_transition: params MUST contain "from_state", "to_state", AND "event". Never omit "event".
- For add_square: if "States eligible for expansion" is not "(none)", params MUST include "parent_id" set to one of those IDs.
- For add_square: a and o MUST be different values; e and i MUST be different values. If the user's input would violate this, use operation "unknown" and explain the constraint.
- For generate_code: params.format must be "class", "transition", or "qt".
- For check_states: params.states must be a JSON array of strings.
- For add_square with no explicit parent, omit parent_id from params.
- For add_square: if fewer than 4 corners are given, infer the missing ones using the Square of Opposition:
    A (universal affirmative)  is contradictory to O (particular negative)   → if A is known, O = negation of A; and vice-versa.
    E (universal negative)     is contradictory to I (particular affirmative) → if E is known, I = negation of E; and vice-versa.
    A and E are contrary  (cannot both be true).
    I and O are subcontrary (cannot both be false).
  Use these rules to produce a logically consistent set of 4 assertions. The inferred assertions must describe the same conceptual domain as the ones supplied.
- For add_square: the values of a, e, i, o MUST express only the new square's own logic — never include or echo the parent state's assertion string. The parent state is context only.\
"""

        try:
            raw = await asyncio.wait_for(
                self._llm_agent._call_llm(prompt, temperature=0.1),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            result = {
                "operation": "unknown",
                "params": {},
                "message": "I didn't understand that — please try rephrasing your command.",
            }
            logger.info("[BotAgent] operation: %s", json.dumps(result, ensure_ascii=False))
            return result

        cleaned = raw.strip()
        cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned.strip())

        try:
            parsed = json.loads(cleaned)
            result = {
                "operation": parsed.get("operation", "unknown"),
                "params": parsed.get("params", {}),
                "message": parsed.get("message", ""),
            }
        except json.JSONDecodeError:
            result = {
                "operation": "unknown",
                "params": {},
                "message": "I could not parse the response. Please try rephrasing.",
            }

        logger.info("[BotAgent] operation: %s", json.dumps(result, ensure_ascii=False))
        return result