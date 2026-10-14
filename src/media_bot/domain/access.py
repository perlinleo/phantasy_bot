from enum import StrEnum


class AccessDecision(StrEnum):
    OWNER = "owner"
    ALLOWED = "allowed"
    DENIED = "denied"
