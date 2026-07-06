def sanitize_input(value: str) -> str:
    """Very small sanitizer placeholder. Real implementation must be robust."""
    return value.replace("\n", " ").strip()
