from textual.markup import escape

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
        c if c.isalnum() or c == "-" else "-"
        for c in sanitized
        if c.isalnum() or c in "-_ "
    )

    # Remove consecutive hyphens
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")

    return sanitized

if __name__ == '__main__':
    print(sanitize_project_id_search(""))
    print(sanitize_project_id_search("-"))
    print(sanitize_project_id_search("--"))
    print(sanitize_project_id_search(" "))