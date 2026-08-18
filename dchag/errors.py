class DCHAGError(Exception):
    """Base exception."""

class ConfigError(DCHAGError):
    """Invalid model configuration."""

class InterventionError(DCHAGError):
    """Invalid intervention."""
