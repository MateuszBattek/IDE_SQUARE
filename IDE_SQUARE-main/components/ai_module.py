import asyncio
import json
import logging
import os
import threading
import traceback
import uuid
from typing import Any, Callable, Dict, Optional, List

import websockets

from PyQt5.QtCore import QObject, pyqtSignal

from components.fsm_components.state import State
from components.fsm_components.fsm import LogicalSquareFSM

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ide.agent_client")

AgentEventHandler = Callable[[Dict[str, Any]], None]

DEFAULT_BASE_URL = os.getenv("SP2_AGENT_URL", "http://127.0.0.1:8000")


class AgentWorkerSignals(QObject):
    """Qt signals for communicating from worker thread to main thread."""
    event_received = pyqtSignal(dict)  # Emitted for each WS message
    finished = pyqtSignal(dict)        # Emitted with final result
    error = pyqtSignal(str)            # Emitted on error


class AgentServiceClient:
    """
    Client for the SP2 agent service (WebSocket streaming).
    Uses threading to avoid blocking the Qt main thread.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, session_id: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.signals = AgentWorkerSignals()
        self._worker_thread: Optional[threading.Thread] = None
        logger.info(f"AgentServiceClient initialized. base_url={self.base_url}")

    def _run_async_in_thread(self, prompt: str) -> None:
        """Run the async WebSocket call in a new event loop in this thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._stream_ws(prompt))
            self.signals.finished.emit(result)
        except Exception as exc:
            logger.error(f"Worker thread error: {exc}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            self.signals.error.emit(str(exc))
        finally:
            loop.close()

    async def _stream_ws(self, prompt: str) -> Dict[str, Any]:
        ws_url = self.base_url.replace("http", "ws") + "/workflow"
        logger.info(f"[WS] Connecting to {ws_url}...")

        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info(f"[WS] Connected successfully")

                payload = {"requirements": prompt, "session_id": self.session_id}
                logger.debug(f"[WS] Sending: {json.dumps(payload)[:200]}...")
                await websocket.send(json.dumps(payload))
                logger.debug(f"[WS] Sent initial message")

                final_payload: Dict[str, Any] = {}
                msg_count = 0

                async for raw in websocket:
                    msg_count += 1
                    logger.debug(f"[WS] Received message #{msg_count}: {str(raw)[:200]}...")

                    try:
                        message = json.loads(raw)
                    except json.JSONDecodeError as e:
                        logger.error(f"[WS] Failed to parse message: {e}")
                        continue

                    msg_type = message.get("type", "unknown")
                    logger.info(f"[WS] Message #{msg_count} type={msg_type}")

                    if msg_type == "session":
                        self.session_id = message.get("session_id", self.session_id)
                        logger.info(f"[WS] Session ID set to: {self.session_id}")

                    if msg_type == "error":
                        error_msg = message.get("error", "unknown error")
                        logger.error(f"[WS] Server error: {error_msg}")

                    # Emit signal for each message (will be received on main thread)
                    self.signals.event_received.emit(message)

                    if msg_type == "final":
                        final_payload = message.get("data", {})
                        states_count = len(final_payload.get("state_machine", {}).get("states", []))
                        logger.info(f"[WS] Final payload received: {states_count} states")
                        break

                logger.info(f"[WS] Stream ended after {msg_count} messages")

                if final_payload.get("session_id"):
                    self.session_id = final_payload["session_id"]

                return final_payload

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"[WS] Connection closed: code={e.code}, reason={e.reason}")
            raise
        except Exception as e:
            logger.error(f"[WS] Connection error: {e}")
            logger.error(f"[WS] Traceback:\n{traceback.format_exc()}")
            raise

    def send_prompt_async(self, prompt: str) -> None:
        """
        Send prompt over WebSocket in a background thread.
        Connect to signals.event_received, signals.finished, signals.error
        to receive results.
        """
        logger.info(f"send_prompt_async called with prompt: {prompt[:100]}...")

        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning("Previous request still in progress")
            return

        self._worker_thread = threading.Thread(
            target=self._run_async_in_thread,
            args=(prompt,),
            daemon=True
        )
        self._worker_thread.start()
        logger.info("Worker thread started")

    def send_prompt(
        self, prompt: str, on_event: Optional[AgentEventHandler] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version (blocks). Use send_prompt_async for non-blocking.
        """
        logger.info(f"send_prompt called with prompt: {prompt[:100]}...")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Temporarily connect on_event if provided
            if on_event:
                self.signals.event_received.connect(on_event)

            result = loop.run_until_complete(self._stream_ws(prompt))
            logger.info(f"send_prompt completed successfully")
            return result
        except Exception as exc:
            logger.error(f"send_prompt failed: {exc}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise RuntimeError(f"WebSocket call failed: {exc}") from exc
        finally:
            if on_event:
                try:
                    self.signals.event_received.disconnect(on_event)
                except TypeError:
                    pass
            loop.close()


def format_messages(messages: List[Dict[str, Any]]) -> str:
    """Render agent messages as plain text."""
    logger.debug(f"format_messages called with {len(messages)} messages")
    lines = []
    for msg in messages:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def apply_state_machine_to_fsm(fsm: LogicalSquareFSM, state_machine: Dict[str, Any]) -> None:
    """
    Map agent-generated state machine into the IDE's LogicalSquareFSM.
    This resets the current FSM with a flat tree rooted at '0'.
    """
    logger.info("apply_state_machine_to_fsm called")
    logger.debug(f"state_machine data: {json.dumps(state_machine)[:500]}...")

    states = state_machine.get("states", [])
    transitions = state_machine.get("transitions", [])

    logger.info(f"Processing {len(states)} states and {len(transitions)} transitions")

    # Reset FSM structure
    fsm.span_tree = {}
    fsm.root = "0"
    root_state = State(state_id="0", assertion="Root state", name="Root")
    fsm.span_tree[fsm.root] = {"state": root_state, "children": []}
    fsm.current_id = 1
    fsm.suffix_index = 0
    fsm.attributes = []
    fsm.latest_states = []
    fsm.transitions = []
    fsm.state_transitions_map = {}

    name_to_id: Dict[str, str] = {}
    for idx, state in enumerate(states, start=1):
        sid = str(idx)
        name = state.get("name") or sid
        description = state.get("description") or name
        logger.debug(f"  Adding state: id={sid}, name={name}")
        node = State(state_id=sid, assertion=description, name=name)
        fsm.span_tree[sid] = {"state": node, "children": []}
        fsm.span_tree[fsm.root]["children"].append(sid)
        name_to_id[name] = sid
        fsm.latest_states.append(sid)

    for transition in transitions:
        from_state = transition.get("from_state") or transition.get("from")
        to_state = transition.get("to_state") or transition.get("to")
        label = transition.get("condition") or transition.get("action") or "transition"

        mapped_from = name_to_id.get(from_state, from_state)
        mapped_to = name_to_id.get(to_state, to_state)
        if mapped_from and mapped_to:
            logger.debug(f"  Adding transition: {mapped_from} -> {mapped_to} [{label}]")
            fsm.add_transition(mapped_from, mapped_to, label)
        else:
            logger.warning(f"  Skipping transition: from={from_state}, to={to_state} (mapping failed)")

    logger.info(f"FSM updated: {len(fsm.latest_states)} states, {len(fsm.transitions)} transitions")
