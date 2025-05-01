from secrets_manager.utils.helpers import format_error_message, sanitize_project_id_search


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
