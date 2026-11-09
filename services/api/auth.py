"""Authentication utilities for the ASE Web API"""

import uuid

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

def current_user():
    """Returns the current user ID. For testing now it is always the same"""
    return DEV_USER_ID