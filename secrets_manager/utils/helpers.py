import json
import pathlib
from hashlib import sha256
from typing import IO


def format_error_message(error_message: str, max_length: int | None = None) -> str:
    """
    Format the error message for display.
    Truncate if too long.
    """
    if max_length:
        if len(error_message) > max_length:
            error_message = error_message[:max_length] + " ..."
    return error_message


def sanitize_project_id_search(search_term: str) -> str:
    """
    Sanitizes a search term to contain only characters permitted in GCP project IDs.

    Args:
        search_term (str): The search term to sanitize

    Returns:
        str: Sanitized string containing only lowercase letters, numbers, and hyphens

    Example:
        >>> sanitize_project_id_search("My Project 123!")
        'my-project-123'
    """
    # Convert to lowercase
    sanitized = search_term.lower()

    # Replace spaces and invalid characters with hyphens
    # Keep only allowed characters: lowercase letters, numbers, and hyphens
    sanitized = "".join(
        c if c.isalnum() or c == "-" else "-" for c in sanitized if c.isalnum() or c in "-_ "
    )

    # Remove consecutive hyphens
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")

    return sanitized


def sanitize_secrets(data: dict) -> dict:
    """Sanitize all values in a dictionary while preserving keys.

    Args:
        data: Dictionary containing secret data

    Returns:
        Dict with all values sanitized but keys preserved
    """

    def _mask_value(value: str | int | float | bool) -> str:
        """Mask any value while preserving some structure."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int | float):
            return "**NUMBER**"

        str_value = str(value)
        if len(str_value) <= 4:
            return "*" * len(str_value)
        return f"{str_value[:2]}{'*' * (len(str_value) - 4)}{str_value[-2:]}"

    def _sanitize_recursive(obj):
        """Recursively sanitize values in nested structures."""
        if isinstance(obj, dict):
            return {k: _sanitize_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_sanitize_recursive(item) for item in obj]
        else:
            return _mask_value(obj)

    return _sanitize_recursive(data)


def validate_json_content(filelike: IO) -> dict | None:
    filelike.seek(0)
    return json.load(filelike)


# thanks to https://www.quickprogrammingtips.com/python/how-to-calculate-sha256-hash-of-a-file-in-python.html
def shasum(file: pathlib.Path):
    sha256_hash = sha256()
    with open(file, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
