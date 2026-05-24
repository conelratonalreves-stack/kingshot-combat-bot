"""Data validation utilities."""

def validate_troop_count(count: int) -> bool:
    """Validate troop count is non-negative."""
    return isinstance(count, int) and count >= 0


def validate_stat_range(value: float) -> bool:
    """Validate stat value is in reasonable range."""
    return isinstance(value, (int, float)) and 0 <= value <= 10000


def validate_percentage(value: float) -> bool:
    """Validate value is between 0 and 1."""
    return isinstance(value, (int, float)) and 0 <= value <= 1


def validate_formation(infantry: float, cavalry: float, archers: float) -> dict:
    """Validate troop formation adds up to 100% with minimum 5% each.
    
    Returns dict with 'valid' and 'error' keys.
    """
    # Check types
    if not all(isinstance(x, (int, float)) for x in [infantry, cavalry, archers]):
        return {
            "valid": False,
            "error": "All formations must be numbers"
        }
    
    # Check percentages
    if not all(0 <= x <= 1 for x in [infantry, cavalry, archers]):
        return {
            "valid": False,
            "error": "All formations must be between 0 and 1"
        }
    
    # Check total is approximately 1
    total = infantry + cavalry + archers
    if abs(total - 1.0) > 0.01:
        return {
            "valid": False,
            "error": f"Total formation must equal 1.0 (100%), got {total:.2f}"
        }
    
    # Check minimum 5% each
    if infantry < 0.05 or cavalry < 0.05 or archers < 0.05:
        return {
            "valid": False,
            "error": "Each troop type must be at least 5% (0.05)"
        }
    
    return {"valid": True, "error": None}
