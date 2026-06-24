"""
validators.py — Shared validation helpers.

These helpers are used by the service layer as a second validation gate,
independent of the Pydantic schema validation that runs at the HTTP boundary.

Having two validation layers means:
- The schema layer rejects obviously bad input early (before DB I/O).
- The service layer can apply business-rule validation with access to DB state
  (e.g. checking user-level limits in future iterations).
"""


class AmountValidationError(ValueError):
    """Raised when an amount fails business-rule validation."""
    pass


def validate_amount(amount: float) -> None:
    """
    Enforce amount business rules:

    1. Must be a real number (not NaN or Infinity — Python's float allows these).
    2. Must be strictly greater than zero.
       - Zero:     No economic value; likely a client bug.
       - Negative: Potential abuse vector (score manipulation, balance drain).

    Raises AmountValidationError with a descriptive message on failure.
    """
    import math

    if math.isnan(amount) or math.isinf(amount):
        raise AmountValidationError("Amount must be a finite number")

    if amount <= 0:
        raise AmountValidationError(
            f"Amount must be greater than zero, got {amount}"
        )


def validate_non_blank(value: str, field_name: str) -> str:
    """
    Reject None, empty string, or whitespace-only strings.

    Returns the stripped value on success.
    Raises ValueError on failure.
    """
    if not value or not value.strip():
        raise ValueError(f"'{field_name}' must not be blank")
    return value.strip()
