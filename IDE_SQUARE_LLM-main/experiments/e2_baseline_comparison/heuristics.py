"""
Heuristics and configuration for B2 (Manual Square) approach.

Contains:
- State keywords for lifecycle detection
- Lifecycle ordering for transition generation
- Initial/Final state classification
"""

# State keywords to identify lifecycle states (covers all test cases)
STATE_KEYWORDS = [
    # Order/general
    "pending", "processing", "processed", "completed", "cancelled",
    "active", "inactive", "reserved", "available", "occupied",
    "new", "approved", "rejected", "shipped", "delivered",
    "open", "closed", "suspended", "archived",
    # Document workflow
    "draft", "review", "reviewed",
    # User account
    "deleted", "verified",
    # Ticket support
    "assigned", "resolved", "escalated",
    # Payment
    "authorized", "declined", "captured", "refunded", "flagged",
    # Inventory
    "in_stock", "backordered", "out_of_stock"
]

# Lifecycle ordering for transition generation
# States are ordered by typical progression in a lifecycle
LIFECYCLE_ORDER = [
    # Initial states
    "new", "draft", "open", "in_stock",
    # Early stages
    "pending", "inactive", "available", "assigned",
    # Middle stages  
    "review", "reserved", "active", "authorized",
    # Processing
    "processing", "in_progress", "captured",
    # Near-final
    "shipped", "resolved", "approved", "suspended",
    # Final states
    "completed", "delivered", "closed", "refunded",
    # Terminal/negative states
    "cancelled", "rejected", "declined", "deleted", "archived", "inactive", "backordered"
]

# States that are considered initial (starting points)
INITIAL_STATES = [
    "pending", "new", "available", "draft", "open", "in_stock", "inactive"
]

# States that are considered final (end points)
FINAL_STATES = [
    "completed", "cancelled", "delivered", "closed", "rejected", 
    "declined", "deleted", "refunded", "shipped", "resolved", "approved"
]


def is_initial_state(state_name: str) -> bool:
    """Check if a state name indicates an initial state."""
    name_lower = state_name.lower()
    return any(keyword in name_lower for keyword in INITIAL_STATES)


def is_final_state(state_name: str) -> bool:
    """Check if a state name indicates a final state."""
    name_lower = state_name.lower()
    return any(keyword in name_lower for keyword in FINAL_STATES)


def get_lifecycle_order(state_name: str) -> int:
    """
    Get the lifecycle order index for a state.
    Lower index = earlier in lifecycle.
    Returns 100 for unknown states.
    """
    name_lower = state_name.lower()
    for i, keyword in enumerate(LIFECYCLE_ORDER):
        if keyword in name_lower:
            return i
    return 100
