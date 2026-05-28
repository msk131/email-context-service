"""API v1 routes.

All v1 routes are imported here for main.py to register.
"""
from app.api.v1 import clients, emails, firms, setup, summaries

__all__ = ["clients", "emails", "firms", "setup", "summaries"]
