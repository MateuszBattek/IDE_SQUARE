from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

# Podstawowa klasa do tworzenia agentów 
class BaseAgent(ABC):
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        try:
            logger.info(f"Agent {self.name} starting processing")
            result = await self.process(input_data)
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "agent_name": self.name,
                "success": True,
                "result": result,
                "processing_time_ms": processing_time,
                "error_message": None
            }
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Agent {self.name} failed: {str(e)}")
            
            return {
                "agent_name": self.name,
                "success": False,
                "result": None,
                "processing_time_ms": processing_time,
                "error_message": str(e)
            }