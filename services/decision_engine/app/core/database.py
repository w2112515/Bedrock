"""
Database connection and session management for DecisionEngine Service.
Reuses shared database utilities.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.database import engine, SessionLocal, Base, get_db

# Re-export for convenience
__all__ = ["engine", "SessionLocal", "Base", "get_db"]

