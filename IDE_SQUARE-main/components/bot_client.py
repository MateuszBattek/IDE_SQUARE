import json
import logging
import os
import socket
import threading
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger("ide.bot_client")

DEFAULT_BASE_URL = os.getenv("SP2_AGENT_URL", "http://127.0.0.1:8000")


class BotClientSignals(QObject):
    response_received = pyqtSignal(dict)
    error = pyqtSignal(str)


class BotServiceClient:
    """HTTP client for the /bot/intent endpoint. Runs the request in a background thread."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.signals = BotClientSignals()
        self._worker: Optional[threading.Thread] = None

    def send_message_async(self, message: str, fsm_context: Dict[str, Any]) -> None:
        if self._worker and self._worker.is_alive():
            logger.warning(
                "Previous bot request still in progress — ignoring new request"
            )
            return
        self._worker = threading.Thread(
            target=self._post,
            args=(message, fsm_context),
            daemon=True,
        )
        self._worker.start()

    def _post(self, message: str, fsm_context: Dict[str, Any]) -> None:
        url = f"{self.base_url}/bot/intent"
        payload = json.dumps({"message": message, "fsm_context": fsm_context}).encode(
            "utf-8"
        )
        logger.info(f"[bot] POST {url}  message={message[:80]!r}")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
                logger.info(f"[bot] response: operation={result.get('operation')}")
                self.signals.response_received.emit(result)
        except urllib.error.URLError as exc:
            logger.error(f"[bot] connection error: {exc}")
            reason = exc.reason
            if isinstance(reason, ConnectionRefusedError):
                self.signals.error.emit(
                    "Agent server is not running. Start it with: uv run uvicorn src.main:app"
                )
            else:
                self.signals.error.emit(f"Could not reach the agent server: {reason}")
        except socket.timeout:
            logger.error("[bot] request timed out after 120s")
            self.signals.error.emit(
                "Request timed out — the LLM took too long to respond."
            )
        except Exception as exc:
            logger.error(f"[bot] unexpected error:\n{traceback.format_exc()}")
            self.signals.error.emit(str(exc))

    def _clear_history(self):
        url = f"{self.base_url}/bot/history/clear"
        logger.info(f"[bot] POST {url}")

        try:
            req = urllib.request.Request(
                url,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                pass

        except urllib.error.URLError as exc:
            logger.error(f"[bot] connection error: {exc}")
            reason = exc.reason

            if isinstance(reason, ConnectionRefusedError):
                self.signals.error.emit(
                    "Agent server is not running. Start it with: uv run uvicorn src.main:app"
                )
            else:
                self.signals.error.emit(f"Could not reach the agent server: {reason}")

        except socket.timeout:
            logger.error("[bot] request timed out after 120s")
            self.signals.error.emit(
                "Request timed out — the LLM took too long to respond."
            )

        except Exception as exc:
            logger.error(f"[bot] unexpected error:\n{traceback.format_exc()}")
            self.signals.error.emit(str(exc))

    def _add_to_history(self, message: str):
        url = f"{self.base_url}/bot/history/add"
        logger.info(f"[bot] POST {url} message='{message[:30]}...'")

        try:
            # 1. Przygotowanie danych w formacie JSON
            data = json.dumps({"message": message}).encode("utf-8")

            # 2. Utworzenie requesta z nagłówkiem Content-Type
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                # Odczytujemy odpowiedź (opcjonalnie)
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data

        except urllib.error.URLError as exc:
            logger.error(f"[bot] connection error: {exc}")
            self.signals.error.emit(f"Błąd połączenia: {exc.reason}")
        except Exception as exc:
            logger.error(f"[bot] unexpected error: {exc}")
            self.signals.error.emit(str(exc))
