import json
import pathlib
import tempfile
from io import StringIO
from unittest.mock import mock_open, patch

import pytest

from secrets_manager.utils.helpers import (
    format_error_message,
    sanitize_project_id_search,
    shasum,
    validate_json_content,
)


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
        json.dump({"test": "data"}, f)
        return pathlib.Path(f.name)


class TestFormatErrorMessage:
    def test_basic_message_formatting(self):
        """Test basic error message formatting without truncation."""
        message = "Test error message"
        result = format_error_message(message)
        assert result == "Test error message"

    def test_message_truncation(self):
        """Test error message truncation at specified length."""
        message = "This is a very long error message that needs to be truncated"
        max_length = 20
        result = format_error_message(message, max_length)
        assert len(result) <= max_length + 4  # +4 for " ..."
        assert result.endswith(" ...")
        assert result.startswith("This is a very long")

    def test_no_truncation_when_under_max_length(self):
        """Test that short messages aren't truncated."""
        message = "Short message"
        max_length = 20
        result = format_error_message(message, max_length)
        assert result == message
        assert " ..." not in result

    def test_none_max_length(self):
        """Test formatting with None max_length."""
        message = "Test message without truncation"
        result = format_error_message(message, None)
        assert result == message


class TestSanitizeProjectIdSearch:
    def test_basic_sanitization(self):
        """Test basic string sanitization."""
        test_cases = [
            ("My Project", "my-project"),
            ("test_project_123", "test-project-123"),
            ("DEV Environment", "dev-environment"),
            ("prod.system.v1", "prodsystemv1"),
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected

    def test_consecutive_special_characters(self):
        """Test handling of consecutive special characters."""
        test_cases = [
            ("test__project", "test-project"),
            ("dev---prod", "dev-prod"),
            ("test  project", "test-project"),
            ("test_-_project", "test-project"),
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected

    def test_special_characters_removal(self):
        """Test removal of special characters."""
        test_cases = [
            ("project@123", "project123"),
            ("test!project", "testproject"),
            ("dev$prod", "devprod"),
            ("test#123", "test123"),
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected

    def test_case_conversion(self):
        """Test conversion to lowercase."""
        test_cases = [
            ("TestProject", "testproject"),
            ("DEV_PROD", "dev-prod"),
            ("Test-ENV-123", "test-env-123"),
            ("UPPER_CASE", "upper-case"),
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected

    def test_edge_cases(self):
        """Test edge cases."""
        test_cases = [
            (" ", "-"),  # Single space
            ("---", "-"),  # Only hyphens
            ("___", "-"),  # Only underscores
            ("   ", "-"),  # Multiple spaces
            ("!@#$%", ""),  # Only special characters
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected

    def test_mixed_character_types(self):
        """Test handling of mixed character types."""
        test_cases = [
            ("Dev-123_TEST", "dev-123-test"),
            ("prod_456-STAGING", "prod-456-staging"),
            ("Test__123--DEV", "test-123-dev"),
            ("PROD-456_test", "prod-456-test"),
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected

    def test_preserves_valid_characters(self):
        """Test that valid characters are preserved."""
        test_cases = [
            ("abc123", "abc123"),
            ("dev-prod", "dev-prod"),
            ("test-123-xyz", "test-123-xyz"),
            ("abcdefghijklmnopqrstuvwxyz-0123456789", "abcdefghijklmnopqrstuvwxyz-0123456789"),
        ]
        for input_str, expected in test_cases:
            assert sanitize_project_id_search(input_str) == expected


def test_validate_json_content_valid():
    """Test validate_json_content with valid JSON data."""
    # Create a file-like object with valid JSON
    valid_json = '{"key": "value", "number": 42}'
    file_obj = StringIO(valid_json)

    result = validate_json_content(file_obj)

    assert result == {"key": "value", "number": 42}


def test_validate_json_content_invalid():
    """Test validate_json_content with invalid JSON data."""
    # Create a file-like object with invalid JSON
    invalid_json = '{"key": "value", invalid}'
    file_obj = StringIO(invalid_json)

    with pytest.raises(json.JSONDecodeError):
        validate_json_content(file_obj)


def test_validate_json_content_empty():
    """Test validate_json_content with empty file."""
    file_obj = StringIO("")

    with pytest.raises(json.JSONDecodeError):
        validate_json_content(file_obj)


def test_shasum_with_file(temp_json_file):
    """Test shasum with an actual file."""
    import hashlib

    # Calculate hash of known content
    known_content = json.dumps({"test": "data"}).encode()
    expected_hash = hashlib.sha256(known_content).hexdigest()

    # Calculate hash using shasum function
    result = shasum(temp_json_file)

    assert result == expected_hash


def test_shasum_with_large_file():
    """Test shasum with a large file to verify chunked reading."""
    import hashlib

    # Mock a large file with known content
    large_content = b"x" * 8192  # Two 4K blocks
    expected_hash = hashlib.sha256(large_content).hexdigest()

    mock_file = mock_open(read_data=large_content)
    with patch("builtins.open", mock_file):
        result = shasum(pathlib.Path("dummy.txt"))

    assert result == expected_hash
    # Verify that the file was read in chunks
    handle = mock_file()
    assert handle.read.call_count > 1


def test_shasum_with_empty_file():
    """Test shasum with an empty file."""
    import hashlib

    # Create empty file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        pass

    file_path = pathlib.Path(f.name)
    try:
        result = shasum(file_path)
        expected_hash = hashlib.sha256(b"").hexdigest()
        assert result == expected_hash
    finally:
        file_path.unlink()


def test_shasum_with_nonexistent_file():
    """Test shasum with a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        shasum(pathlib.Path("nonexistent_file.txt"))


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ('{"key": "value"}', {"key": "value"}),
        ('{"nested": {"key": "value"}}', {"nested": {"key": "value"}}),
        ('{"array": [1, 2, 3]}', {"array": [1, 2, 3]}),
        ('{"null": null}', {"null": None}),
    ],
)
def test_validate_json_content_various_types(test_input, expected):
    """Test validate_json_content with various JSON data types."""
    file_obj = StringIO(test_input)
    result = validate_json_content(file_obj)
    assert result == expected
