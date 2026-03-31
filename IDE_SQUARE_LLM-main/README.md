# SQUARE IDE - LLM-driven Multi-Agent System

## Overview

SQUARE IDE is a prototype system for generating formal logic models and state machines from natural language requirements using the Square of Opposition logical framework (A, E, I, O relations).

## Installation

1. **Install dependencies:**
```bash
uv sync
```

## Quick Start

### Basic Usage

```bash
# Process requirements using the CLI
python -m src.main process "All traffic lights have red states. No red states are green states."

# Save output to file
python -m src.main process "An elevator system where all floors have call buttons" --output results.json

# Verbose output
python -m src.main process "A vending machine system" --verbose
```

### Python API

```python
import asyncio
from src.orchestration.langgraph_workflow import SquareIDEWorkflow

async def main():
    workflow = SquareIDEWorkflow()
    
    requirements = """
    A traffic light system where:
    - All red states exclude green states
    - Some yellow states precede red states
    """
    
    result = await workflow.run(requirements)
    print(result)

asyncio.run(main())
```

### Run the Agent Service (WebSocket-only)

```bash
# start FastAPI service (WS /workflow) with sqlite sessions
python -m src.main serve --host 127.0.0.1 --port 8000
```

- Env vars: `OPENAI_API_KEY` (required), `SQUARE_IDE_DB_PATH` (optional sqlite path), `OPENAI_MODEL` (optional).
- WebSocket stream: connect to `ws://127.0.0.1:8000/workflow`, send `{"requirements": "...", "session_id": "<optional>"}`, receive `event` updates and a `final` payload with models.

## Project Structure

```
SP2/
├── src/
│   ├── agents/           # Individual agent implementations
│   │   ├── logic_agent.py     # SQUARE logic extraction
│   │   ├── state_agent.py     # State machine generation
│   │   ├── llm_agent.py       # LLM coordination
│   │   └── base_agent.py      # Abstract base class
│   ├── orchestration/    # LangGraph workflow
│   │   └── langgraph_workflow.py
│   ├── models/           # Pydantic data models
│   ├── config.py         # Configuration management
│   └── main.py          # CLI interface
├── experiments/         # Evaluation experiments
├── examples/           # Example requirements
└── tests/             # Unit tests
```

## Architecture

### Agents

1. **LogicAgent**: Extracts A/E/I/O relations from natural language
2. **StateAgent**: Converts logic relations into state machines with intelligent entity classification
   - Distinguishes between state entities (concrete nouns with lifecycle) and attributes (properties/qualities)
   - Uses LLM-based semantic analysis for context-aware classification
   - Falls back to heuristic methods when LLM is unavailable
   - Assigns attributes to states based on logical relation types
   - Creates transitions only between actual states, not state-to-attribute pairs
3. **LLMAgent**: Meta-agent coordinator using OpenAI API
4. **ClassAgent**: Generates classes, attributes, assertions and test disjointness (using provers)
5. **ProverAgent**: Integrates with external SAT solvers / theorem provers
6. **VerifierAgent**: Checks consistency and proposes fixes or new states
7. **CodeAgent**: Code generation from models

### StateAgent: Entity Classification

The StateAgent uses a sophisticated approach to distinguish states from attributes:

**Classification Methods**:
1. **LLM-Based (Primary)**: Semantic analysis with full context understanding
   - Analyzes entity meaning within domain context
   - Considers role in logical relations
   - Provides human-readable reasoning for decisions
   
2. **Heuristic (Fallback)**: Linguistic pattern analysis
   - Morphological patterns (adjective suffixes)
   - Relation role frequency (subject vs. predicate)
   - Ensures system works without LLM dependency

**Attribute Assignment Rules**:
- **A (All X are Y)**: Y is "always" true for X
- **E (No X are Y)**: Y is "never" true for X  
- **I (Some X are Y)**: Y is "possible" for X
- **O (Some X are not Y)**: Y is "sometimes_not" true for X

**Example**:
```
Input: "All flights are monitored by the tower"
Classification:
  - "flight" → state (concrete entity)
  - "monitored" → attribute (property)
Result: State "flight" with attribute monitored=always
```

This prevents illogical states like "monitored" becoming a separate state node.

### Workflow

The system uses LangGraph for agent orchestration:
1. LLMAgent interprets requirements
2. LogicAgent extracts formal relations
3. StateAgent generates state machine
4. VerifierAgent checks consistency
5. Iterative refinement based on verification

## Examples

### Traffic Light System

Input:
```
"A traffic light system where all red states exclude green states and some yellow states precede red states"
```

Expected Output:
- Logic relations: E(red, green), I(yellow, precedes_red)
- State machine with Red, Yellow, Green states
- Transitions based on logical constraints

### Elevator System

See `examples/requirements_examples.py` for more examples.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code  
ruff check src/ tests/

# Type checking
mypy src/
```

### Adding New Agents

1. Inherit from `BaseAgent` class
2. Implement `async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]`
3. Add to workflow in `langgraph_workflow.py`

## Configuration

Environment variables (see `.env.template`):

- `OPENAI_API_KEY`: OpenAI API key (required)
- `OPENAI_MODEL`: Model name (default: gpt-4o)
- `LOG_LEVEL`: Logging level (default: INFO)
- `Z3_TIMEOUT_MS`: Z3 solver timeout (default: 30000)

## Experiments

The system includes three evaluation experiments:

### E1: Model Quality (Offline)
```bash
python -m src.main experiment e1
```

### E2: Productivity Study  
```bash
python -m src.main experiment e2
```

### E3: Noise Robustness
```bash
python -m src.main experiment e3
```
