import os
import openai
import google.generativeai as genai
import json
import re
from typing import Dict, Any, Optional, List
from ..agents.base_agent import BaseAgent
from ..config import config


class LLMAgent(BaseAgent):
    def __init__(self, agent_config: Optional[Dict[str, Any]] = None):
        super().__init__("LLMAgent", agent_config)

        self.gemini_enabled = False
        self.openai_client = None

        if config.OLLAMA_MODEL:
            self.openai_client = openai.AsyncOpenAI(
                base_url=config.OLLAMA_BASE_URL,
                api_key="ollama",
            )
            self.model_name = config.OLLAMA_MODEL

        elif config.GEMINI_API_KEY:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)
            self.gemini_enabled = True
            self.model_name = config.GEMINI_MODEL

        elif config.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            self.model_name = config.OPENAI_MODEL

        else:
            raise ValueError(
                "No LLM configured. Set OLLAMA_MODEL (local) or one of: "
                "GEMINI_API_KEY, OPENAI_API_KEY."
            )

    async def _call_llm(self, prompt: str, temperature: float = 0.1) -> str:
        if self.gemini_enabled:
            generation_config = {"temperature": temperature}
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )
            return response.text
        else:
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return response.choices[0].message.content

    def _normalize_entity(self, text: str) -> str:
        """
        Normalize entity text to snake_case format.
        Examples:
            "premium rooms" -> "premium_room"
            "have a balcony" -> "balcony"
            "are air-conditioned" -> "air_conditioned"
            "available for reservation" -> "available"
        """
        text = text.lower().strip()

        # Remove leading verb phrases like "have a", "are", "is", etc.
        text = re.sub(r"^(have|has)\s+(a|an|the)\s+", "", text)
        text = re.sub(r"^(is|are|be|being|been)\s+", "", text)
        text = re.sub(r"^(a|an|the)\s+", "", text)

        # Remove common suffixes for properties
        text = re.sub(r"\s+for\s+(reservation|booking|use|service).*$", "", text)

        # Replace hyphens and spaces with underscores
        text = re.sub(r"[-\s]+", "_", text)

        # Remove trailing 's' for plurals (with exceptions)
        if text.endswith("s") and not text.endswith(("ss", "us", "is")):
            text = text[:-1]

        # Remove any non-alphanumeric characters except underscores
        text = re.sub(r"[^a-z0-9_]", "", text)

        return text

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = input_data.get("task_type", "extract_requirements")

        if task_type == "extract_requirements":
            return await self._extract_requirements(input_data)
        elif task_type == "coordinate_agents":
            return await self._coordinate_agents(input_data)
        elif task_type == "infer_logic_square": 
            return await self._infer_square_relations(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _extract_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_input = input_data.get("user_input", "")

        prompt = f"""
        Analyze the following user input and extract formal logical requirements according to the Square of Opposition.

        User Input: {user_input}

        Extract logical formulas and identify:
        1. Universal affirmative relations (A): "All X are Y"
        2. Universal negative relations (E): "No X are Y" 
        3. Particular affirmative relations (I): "Some X are Y"
        4. Particular negative relations (O): "Some X are not Y"

        For each relation, extract:
        - The exact subject (X)
        - The exact predicate (Y)
        - The source statement from the input
        - Confidence level (0.0 to 1.0)

        Also identify:
        - All entities mentioned (states, conditions, objects)
        - Potential state transitions
        - Temporal constraints
        - Any ambiguities that need clarification

        Format your response strictly as a JSON object:
        {{
            "formulas": [
                {{
                    "type": "universal_affirmative" | "universal_negative" | "particular_affirmative" | "particular_negative",
                    "subject": "extracted subject",
                    "predicate": "extracted predicate",
                    "source_text": "original statement",
                    "confidence": 0.95
                }}
            ],
            "entities": ["entity1", "entity2", ...],
            "states": ["state1", "state2", ...],
            "transitions": [
                {{
                    "from": "state1",
                    "to": "state2",
                    "condition": "optional condition"
                }}
            ],
            "ambiguities": ["note about any unclear parts"],
            "overall_confidence": 0.85
        }}
        """

        interpretation = await self._call_llm(prompt, temperature=0.1)

        if interpretation.startswith("```json"):
            interpretation = interpretation[len("```json") :].strip()
        if interpretation.endswith("```"):
            interpretation = interpretation[:-3].strip()

        try:
            requirements = json.loads(interpretation)
        except json.JSONDecodeError:
            requirements = {
                "formulas": [],
                "entities": [],
                "error": "Failed to parse LLM response",
            }

        # Normalize all entities and predicates in formulas
        for formula in requirements.get("formulas", []):
            if "subject" in formula:
                formula["subject"] = self._normalize_entity(formula["subject"])
            if "predicate" in formula:
                formula["predicate"] = self._normalize_entity(formula["predicate"])

        # Normalize entities list
        if "entities" in requirements:
            requirements["entities"] = [
                self._normalize_entity(entity) for entity in requirements["entities"]
            ]
            # Remove duplicates while preserving order
            seen = set()
            unique_entities = []
            for entity in requirements["entities"]:
                if entity not in seen and entity:  # Skip empty strings
                    seen.add(entity)
                    unique_entities.append(entity)
            requirements["entities"] = unique_entities

        # Normalize states list
        if "states" in requirements:
            requirements["states"] = [
                self._normalize_entity(state) for state in requirements["states"]
            ]

        # Normalize transitions
        for transition in requirements.get("transitions", []):
            if "from" in transition:
                transition["from"] = self._normalize_entity(transition["from"])
            if "to" in transition:
                transition["to"] = self._normalize_entity(transition["to"])

        return {
            "requirements": requirements,
            "needs_clarification": len(requirements.get("ambiguities", [])) > 0,
            "confidence": requirements.get("overall_confidence", 0.5),
        }

    async def _coordinate_agents(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        current_results = input_data.get("agent_results", {})
        target_goal = input_data.get("goal", "")

        prompt = f"""
        As a meta-agent coordinator, analyze the current progress and determine next steps:
        
        Goal: {target_goal}
        Current Results: {current_results}
        
        Determine:
        1. Which agents should run next?
        2. What input data should be provided to each agent?
        3. Are there any conflicts or inconsistencies to resolve?
        4. What is the overall progress toward the goal?
        
        Provide a coordination plan with specific next steps.
        """

        llm_response = await self._call_llm(prompt, temperature=0.2)

        return {
            "coordination_plan": llm_response,
            "next_agents": self._extract_next_agents(llm_response),
            "overall_progress": self._assess_progress(current_results),
        }

    def _check_ambiguity(self, text: str) -> bool:
        ambiguity_indicators = [
            "unclear",
            "ambiguous",
            "multiple interpretations",
            "could mean",
            "might be",
            "possibly",
            "potentially",
        ]
        return any(indicator in text.lower() for indicator in ambiguity_indicators)

    def _assess_confidence(self, text: str) -> float:
        if "certain" in text.lower() or "clear" in text.lower():
            return 0.9
        elif "likely" in text.lower() or "probable" in text.lower():
            return 0.7
        elif "possible" in text.lower() or "might" in text.lower():
            return 0.5
        else:
            return 0.6

    def _extract_next_agents(self, plan: str) -> List[str]:
        agents = []
        if "logic" in plan.lower():
            agents.append("LogicAgent")
        if "state" in plan.lower():
            agents.append("StateAgent")
        if "proof" in plan.lower() or "verif" in plan.lower():
            agents.append("ProverAgent")
        return agents

    def _assess_progress(self, results: Dict[str, Any]) -> float:
        # Count non-empty results (logic_model, ontology_model, state_machine, verification_results)
        completed = 0
        if results.get("logic_model"):
            completed += 1
        if results.get("ontology_model"):
            completed += 1
        if results.get("state_machine"):
            completed += 1
        if results.get("verification_results"):
            completed += 1

        total_expected = 4  # Logic, Ontology, State, Verifier
        return min(completed / total_expected, 1.0) if total_expected > 0 else 0.0
    
    
    async def _infer_square_relations(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer the missing three relations of the Square of Opposition
        from one *true* given relation.

        Output includes:
        - canonical statement (logical form)
        - natural-language paraphrase
        - status for A/E/I/O
        """

        input_relation = input_data.get("relation", {})

        if not input_relation or not all(k in input_relation for k in ["type", "subject", "predicate"]):
            raise ValueError("Input relation must contain 'type', 'subject', and 'predicate'.")

        relation_type = input_relation["type"]
        subject = self._normalize_entity(input_relation["subject"])
        predicate = self._normalize_entity(input_relation["predicate"])

        prompt = f"""
        A logical relation from the Square of Opposition is known to be TRUE.

        Given:
        Relation type: {relation_type}
        Subject (S): {subject}
        Predicate (P): {predicate}

        Using the classical Square of Opposition, infer the remaining three relations 
        (A, E, I, O) for the SAME S and P.

        For each inferred relation, provide:
        - "type": universal_affirmative | universal_negative | particular_affirmative | particular_negative
        - "square_label": A | E | I | O
        - "status": TRUE | FALSE | UNDETERMINED
        - "statement": the formal logical sentence (e.g., "All S are P.")
        - "natural_language": a plain English paraphrase

        The JSON MUST have the structure:

        {{
            "inferred_relations": [
                {{
                    "type": "",
                    "square_label": "",
                    "status": "",
                    "statement": "",
                    "natural_language": ""
                }}
            ]
        }}
        """

        llm_raw = await self._call_llm(prompt, temperature=0.05)
        cleaned = llm_raw

        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json") :].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
            inferred = parsed.get("inferred_relations", [])

            if not isinstance(inferred, list) or len(inferred) != 3:
                raise ValueError("Incorrect number of inferred relations.")

            # Ensure all fields exist; if missing → fallback
    
            for relation in inferred:
                if not all(k in relation for k in ["type", "square_label", "status"]):
                    raise ValueError("Malformed relation fields.")

            return {"inferred_relations": inferred}

        except Exception:
            # If parsing fails - deterministic fallback
            return {
                "inferred_relations": None 
            }


    # ───────────────────────────────────────────────
    # Helper: canonical statements for A/E/I/O
    # ───────────────────────────────────────────────
    def _square_statement(self, label: str, s: str, p: str) -> str:
        if label == "A":
            return f"All {s} are {p}."
        if label == "E":
            return f"No {s} are {p}."
        if label == "I":
            return f"Some {s} are {p}."
        if label == "O":
            return f"Some {s} are not {p}."
        return ""

    # ───────────────────────────────────────────────
    # Helper: natural-language paraphrases
    # ───────────────────────────────────────────────
    def _square_natural(self, label: str, s: str, p: str) -> str:
        if label == "A":
            return f"Every {s} belongs to the group of {p}."
        if label == "E":
            return f"There are no {s} that are also {p}."
        if label == "I":
            return f"At least one {s} is also a {p}."
        if label == "O":
            return f"At least one {s} does not belong to the group of {p}."
        return ""
