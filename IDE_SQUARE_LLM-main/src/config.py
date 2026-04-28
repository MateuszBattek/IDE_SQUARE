import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Explicitly disable LangSmith tracing
# This must be set before any LangChain/LangGraph imports
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""


class Config:
    # Ollama Configuration (local, no API key needed)
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Application Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Prover Settings
    Z3_TIMEOUT_MS: int = int(os.getenv("Z3_TIMEOUT_MS", "30000"))
    ENABLE_EXTERNAL_PROVERS: bool = os.getenv("ENABLE_EXTERNAL_PROVERS", "false").lower() == "true"
    
    # Experiment Settings
    EXPERIMENT_DATA_DIR: str = os.getenv("EXPERIMENT_DATA_DIR", "experiments/results")
    REFERENCE_MODELS_DIR: str = os.getenv("REFERENCE_MODELS_DIR", "experiments/reference_models")
    
    @classmethod
    def validate(cls) -> None:
        if not cls.OLLAMA_MODEL and not cls.GEMINI_API_KEY and not cls.OPENAI_API_KEY:
            raise ValueError(
                "No LLM configured. Set OLLAMA_MODEL (local) or one of: "
                "GEMINI_API_KEY, OPENAI_API_KEY"
            )


config = Config()