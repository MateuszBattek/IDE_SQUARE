import json
import logging
import os
import sqlite3
import traceback
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.config import config
from src.orchestration.langgraph_workflow import SquareIDEWorkflow, WorkflowState

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sp2.server")

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("SQUARE_IDE_DB_PATH", ROOT_DIR / "sessions.db"))

app = FastAPI(title="Square IDE Agent Service", version="0.1.0")
logger.info(f"Server initialized. DB_PATH={DB_PATH}")


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_results (
                session_id TEXT PRIMARY KEY,
                requirements TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def _save_session_result(
    session_id: str, requirements: str, result: dict[str, Any]
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO session_results (session_id, requirements, result_json)
            VALUES (?, ?, ?)
            """,
            (session_id, requirements, json.dumps(result)),
        )
        conn.commit()


def _load_session_result(session_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT result_json FROM session_results WHERE session_id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting up server...")
    _init_db()
    logger.info("Database initialized successfully")


@app.websocket("/workflow")
async def workflow_stream(websocket: WebSocket) -> None:
    """
    Stream workflow execution over WebSocket.
    The client should send a JSON message: {"requirements": "...", "session_id": "optional"}
    """
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"[WS] New connection from {client_host}")
    await websocket.accept()
    logger.debug(f"[WS] Connection accepted from {client_host}")

    try:
        logger.debug("[WS] Waiting for initial message...")
        initial_msg = await websocket.receive_json()
        logger.info(
            f"[WS] Received initial message: {json.dumps(initial_msg)[:200]}..."
        )

        requirements: str = initial_msg.get("requirements", "")
        if not requirements:
            logger.error("[WS] No requirements provided in message")
            raise ValueError("requirements field is required")

        session_id = initial_msg.get("session_id") or f"session-{uuid.uuid4()}"
        logger.info(f"[WS] Session ID: {session_id}")

        await websocket.send_json({"type": "session", "session_id": session_id})
        logger.debug("[WS] Sent session confirmation")

        # Validate config before processing
        logger.debug("[WS] Validating config...")
        config.validate()
        logger.info("[WS] Config validated successfully")

        cached = _load_session_result(session_id)
        if cached:
            logger.info(f"[WS] Found cached result for session {session_id}")
            await websocket.send_json({"type": "final", "data": cached})
            return

        logger.info("[WS] Creating workflow...")
        workflow = SquareIDEWorkflow()
        initial_state = WorkflowState(requirements=requirements).model_dump()
        logger.debug(
            f"[WS] Initial state created with requirements: {requirements[:100]}..."
        )

        # Accumulate the full state from node updates
        accumulated_state: dict[str, Any] = {}
        step_count = 0

        logger.info("[WS] Starting workflow stream...")
        async for update in workflow.graph.astream(
            initial_state, config={"configurable": {"thread_id": session_id}}
        ):
            step_count += 1
            # update is keyed by node name, e.g. {"state_generator": {...state fields...}}
            # Merge the inner state into accumulated_state
            for node_name, node_state in update.items():
                if isinstance(node_state, dict):
                    accumulated_state.update(node_state)
                    current_agent = node_state.get("current_agent", node_name)
                else:
                    current_agent = node_name

            logger.debug(f"[WS] Step {step_count}: node={list(update.keys())}")

            # Send the accumulated state as event so client sees full picture
            await websocket.send_json(
                {
                    "type": "event",
                    "data": {
                        "step": step_count,
                        "node": list(update.keys())[0] if update else "unknown",
                        "state_machine": accumulated_state.get("state_machine", {}),
                        "logic_model": accumulated_state.get("logic_model", {}),
                        "messages": accumulated_state.get("messages", []),
                    },
                }
            )
            logger.debug(f"[WS] Sent event for step {step_count}")

        logger.info(f"[WS] Workflow completed after {step_count} steps")

        payload = {
            "session_id": session_id,
            "logic_model": accumulated_state.get("logic_model", {}),
            "ontology_model": accumulated_state.get("ontology_model", {}),
            "state_machine": accumulated_state.get("state_machine", {}),
            "verification_results": accumulated_state.get("verification_results", []),
            "messages": accumulated_state.get("messages", []),
        }

        states_count = len(payload.get("state_machine", {}).get("states", []))
        transitions_count = len(payload.get("state_machine", {}).get("transitions", []))
        logger.info(
            f"[WS] Final payload: {states_count} states, {transitions_count} transitions"
        )

        _save_session_result(session_id, requirements, payload)
        logger.debug("[WS] Session result saved")

        await websocket.send_json({"type": "final", "data": payload})
        logger.info("[WS] Sent final payload to client")

    except WebSocketDisconnect:
        logger.warning(f"[WS] Client {client_host} disconnected")
        return
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[WS] Error during workflow: {exc}")
        logger.error(f"[WS] Traceback:\n{traceback.format_exc()}")
        await websocket.send_json(
            {"type": "error", "error": str(exc), "detail": "workflow failed"}
        )
        await websocket.close(code=1011)
        logger.info("[WS] Connection closed with error code 1011")


# Bot intent endpoint


class BotIntentRequest(BaseModel):
    message: str
    fsm_context: dict[str, Any] = {}


class HistoryEntry(BaseModel):
    message: str


@app.post("/bot/history/clear")
async def clear_history():
    from src.agents.bot_agent import BotAgent

    bot_agent = BotAgent()
    bot_agent.clear_history()

    return {"message": "Chat history cleared"}


@app.post("/bot/history/add")
async def add_history_entry(entry: HistoryEntry):
    from src.agents.bot_agent import BotAgent

    bot_agent = BotAgent()
    # Dodajemy wiadomość przesłaną w polu "message"
    bot_agent.add_message(entry.message)

    return {
        "status": "success",
        "added": entry.message,
        "history_size": len(bot_agent.chat_history),
    }


@app.post("/bot/intent")
async def bot_intent(request: BotIntentRequest) -> dict[str, Any]:
    """Classify a natural-language command into an IDE operation with parameters."""
    from src.agents.bot_agent import BotAgent
    from src.agents.class_agent import ClassAgent
    from src.agents.logic_agent import LogicAgent
    from src.agents.state_agent import StateAgent
    from src.agents.verifier_agent import VerifierAgent

    from ..models import OntologyModel

    try:
        config.validate()
        bot_agent = BotAgent()
        logic_agent = LogicAgent()
        state_agent = StateAgent()
        class_agent = ClassAgent()
        verifier_agent = VerifierAgent()

        bot_result = await bot_agent.execute(
            {
                "message": request.message,
                "fsm_context": request.fsm_context,
            }
        )
        bot_agent.add_message("User message: " + request.message)

        if not bot_result["success"]:
            return {
                "operation": "error",
                "params": {},
                "message": bot_result["error_message"],
            }

        intent = bot_result["result"]

        if intent["operation"] == "add_square":
            params = intent["params"]

            # Przygotowujemy dane dla LogicAgent
            logic_input = {
                "requirements": {
                    "formulas": [
                        {
                            "type": "universal_affirmative",
                            "subject": "state",
                            "predicate": params.get("a"),
                        },
                        {
                            "type": "universal_negative",
                            "subject": "state",
                            "predicate": params.get("e"),
                        },
                        {
                            "type": "particular_affirmative",
                            "subject": "state",
                            "predicate": params.get("i"),
                        },
                        {
                            "type": "particular_negative",
                            "subject": "state",
                            "predicate": params.get("o"),
                        },
                    ]
                }
            }

            logic_res = await logic_agent.process(logic_input)

            # KROK 3: Jeśli LogicAgent znajdzie sprzeczność, blokujemy operację
            if not logic_res["is_consistent"]:
                # Pobieramy pierwszy opis błędu z listy sprzeczności
                error_msg = logic_res["contradictions"][0]["description"]
                return {
                    "operation": "unknown",
                    "params": {},
                    "message": f"Square verification failed: {error_msg}",
                }

            # Przekształcamy kwadrat logiczny na stany i przejścia
            try:
                state_input = {
                    "logic_model": {
                        "relations": logic_res["logic_model"].get("relations", [])
                    },
                    "requirements": {
                        # Próbujemy wyciągnąć listę stanów z parametrów bota lub z automatu
                        "states": params.get("states", [])
                    },
                    "llm_agent": bot_agent._llm_agent,
                }

                state_result = await state_agent.process(state_input)

                # Zapisujemy wynik maszyny stanów do intencji
                intent["state_machine"] = state_result.get("state_machine")

            except Exception as e:
                logger.error(f"StateAgent Error: {e}")
                # Nie przerywamy, jeśli FSM się nie uda, ale logujemy błąd
                intent["state_machine_error"] = str(e)

            ontology_res = await class_agent.process(
                {"logic_model": logic_input["requirements"]}
            )

            # Jeśli ClassAgent wykryje np. cykle w dziedziczeniu (A->B, B->A)
            ontology_data = ontology_res["ontology"]
            ontology_object = OntologyModel(**ontology_data)
            validation = class_agent.validate_ontology(ontology_object)
            if not validation["is_valid"]:
                return {
                    "operation": "error",
                    "message": f"Błąd struktury ontologii: {validation['issues'][0]['description']}",
                }

            # Dołączamy model ontologii do odpowiedzi dla GUI
            intent["ontology_model"] = ontology_res["ontology"]

            # Przygotowanie paczki wejściowej dla VerifierAgent
            verifier_input = {
                "logic_model": logic_res.get("logic_model"),
                "ontology": ontology_res.get("ontology"),
                "state_machine": state_result.get("state_machine"),
                "requirements": logic_input.get(
                    "requirements", {}
                ),  # Przekazujemy intencje do wykrywania halucynacji
            }
            # Wywołanie procesu weryfikacji (metoda asynchroniczna)
            verification_output = await verifier_agent.process(verifier_input)
            report = verification_output["verification_report"]

            # Jeśli VerifierAgent wykryje błędy o krytyczności "error", blokujemy operację
            if not verification_output["is_consistent"]:
                # Wyciągamy pierwszy poważny błąd (error) z raportu
                critical_issues = [
                    i for i in report.get("issues", []) if i.get("severity") == "error"
                ]
                error_msg = (
                    critical_issues[0]["description"]
                    if critical_issues
                    else "Wykryto niespójność modeli."
                )

                return {
                    "operation": "error",
                    "params": {},
                    "message": f"Błąd spójności systemu: {error_msg}",
                    "verification_report": report,  # Opcjonalnie zwracamy raport do GUI, aby podświetlić błędy
                }

            # Dołączamy sprawdzone, poprawne modele oraz raport (z ew. ostrzeżeniami / warnings) do odpowiedzi dla GUI
            intent["ontology_model"] = ontology_res["ontology"]
            intent["state_machine"] = state_result.get("state_machine")
            intent["verification_results"] = (
                report  # Przekazujemy pełny raport (w tym wygenerowane "fixes")
            )

        bot_agent.add_message("Bot intent: " + str(intent))
        return intent

    except Exception as exc:
        logger.error(f"[bot/intent] {exc}")
        return {"operation": "error", "params": {}, "message": str(exc)}
