"""
Example: Traffic Light System

A traffic light system where:
- All red states exclude green states
- All green states exclude red states  
- Some yellow states precede red states
- Some yellow states precede green states
- No red states are green states
"""

# Simple elevator system
ELEVATOR_SYSTEM = """
An elevator system where:
- All floors have call buttons
- Every elevator has floor indicators
- Some elevators are moving upward
- Some elevators are not moving downward when going up
- No elevators can move up and down simultaneously
- All emergency states override normal operations
"""

# Vending machine
VENDING_MACHINE = """
A vending machine where:
- All coins are accepted when machine is operational
- No coins are accepted when machine is out of order
- Some products are available when machine has inventory
- Some products are not dispensed when payment is insufficient
- Every successful transaction includes product dispensing
- All maintenance modes exclude normal operations
"""

# Complex airport control system
AIRPORT_CONTROL = """
An airport traffic control system where:
- All aircraft on runway exclude other aircraft on same runway
- Every takeoff requires clearance from control tower
- Some aircraft are in holding patterns
- Some aircraft are not cleared for landing during bad weather
- No aircraft can takeoff and land on same runway simultaneously
- All emergency situations override normal flight patterns
- Every aircraft in controlled airspace has assigned flight path
"""