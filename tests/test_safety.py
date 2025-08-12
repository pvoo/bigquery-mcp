"""Test query safety functionality."""

import pytest


@pytest.fixture(autouse=True)
def setup_env(env_vars):
    """Automatically set up environment for all tests."""
    pass  # The env_vars fixture does the actual work


def test_safety_import():
    """Test that we can import the safety function after env setup."""
    from src.bigquery_mcp.query_safety import is_query_safe

    assert is_query_safe is not None


def test_safe_select_queries():
    """Test that safe SELECT queries are allowed."""
    from src.bigquery_mcp.query_safety import is_query_safe

    safe_queries = [
        "SELECT * FROM table",
        "SELECT name, count FROM table WHERE id = 1",
        "select col1, col2 from table",  # lowercase
        "  SELECT * FROM table  ",  # with whitespace
        "WITH cte AS (SELECT * FROM table) SELECT * FROM cte",
        # Newly-allowed safe patterns
        "SELECT 1 ORDER BY 1 DESC",
        "SELECT REPLACE('ab','a','x') AS r",
        "SELECT ';' AS s;",  # semicolon literal inside string plus trailing semicolon
        "SELECT 'a;b' AS s",  # semicolon inside string, no trailing semicolon
    ]

    for query in safe_queries:
        is_safe, _ = is_query_safe(query)
        assert is_safe, f"Query should be safe: {query}"


def test_dangerous_queries():
    """Test that dangerous queries are blocked."""
    from src.bigquery_mcp.query_safety import is_query_safe

    dangerous_queries = [
        "DELETE FROM table WHERE id = 1",
        "UPDATE table SET name = 'test'",
        "INSERT INTO table VALUES (1, 'test')",
        "DROP TABLE test",
        "CREATE TABLE test (id INT)",
        "ALTER TABLE test ADD COLUMN name VARCHAR(50)",
        "TRUNCATE TABLE test",
        "MERGE INTO target USING source ON condition",
        "REPLACE INTO table VALUES (1, 'test')",
        "GRANT SELECT ON table TO user",
        "REVOKE SELECT ON table FROM user",
        "EXEC sp_procedure",
        "EXECUTE sp_procedure",
    ]

    for query in dangerous_queries:
        is_safe, error_msg = is_query_safe(query)
        assert not is_safe, f"Query should be blocked: {query}"
        assert any(phrase in error_msg.lower() for phrase in ("dangerous", "not allowed", "only select and with")), (
            f"Unexpected error message: {error_msg}"
        )


def test_queries_with_comments():
    """Test that queries with comments are properly validated."""
    from src.bigquery_mcp.query_safety import is_query_safe

    # Blocked even with comments
    commented_still_blocked = [
        "-- This is a comment\nDELETE FROM table",  # DML after comment
        "/* comment */ UPDATE table SET col = 'value'",  # DML after block comment
    ]

    for query in commented_still_blocked:
        is_safe, _ = is_query_safe(query)
        assert not is_safe, f"Query should be blocked: {query}"

    # Dangerous only in comments should be allowed
    commented_ignored_dangerous = [
        "SELECT * FROM table; -- DELETE FROM other_table",
        "SELECT * /* DELETE */ FROM table",
    ]

    for query in commented_ignored_dangerous:
        is_safe, _ = is_query_safe(query)
        assert is_safe, f"Query should be allowed (dangerous only in comments): {query}"


def test_multiple_statements_blocked():
    """Ensure multiple statements are rejected while semicolons in strings are fine."""
    from src.bigquery_mcp.query_safety import is_query_safe

    blocked = [
        "SELECT 1; SELECT 2",  # two statements
        "WITH t AS (SELECT 1) ; SELECT 2",  # still two statements when separated by semicolon
    ]

    for query in blocked:
        is_safe, _ = is_query_safe(query)
        assert not is_safe, f"Multiple statements should be blocked: {query}"


def test_non_select_start():
    """Test that queries not starting with SELECT or WITH are blocked."""
    from src.bigquery_mcp.query_safety import is_query_safe

    invalid_start_queries = [
        "SHOW TABLES",
        "DESCRIBE table",
        "EXPLAIN SELECT * FROM table",
    ]

    for query in invalid_start_queries:
        is_safe, error_msg = is_query_safe(query)
        assert not is_safe, f"Query should be blocked: {query}"
        assert "only select and with" in error_msg.lower()


def test_case_insensitive():
    """Test that validation is case insensitive."""
    from src.bigquery_mcp.query_safety import is_query_safe

    mixed_case_dangerous = [
        "delete from table",
        "DeLeTe FrOm table",
        "Delete From table",
    ]

    for query in mixed_case_dangerous:
        is_safe, _ = is_query_safe(query)
        assert not is_safe, f"Query should be blocked regardless of case: {query}"


def test_word_boundaries():
    """Test that keyword detection uses word boundaries."""
    from src.bigquery_mcp.query_safety import is_query_safe

    # These should be safe as the dangerous keywords are part of larger words
    safe_with_keyword_parts = [
        "SELECT * FROM deleted_items",  # 'delete' is part of 'deleted_items'
        "SELECT update_date FROM table",  # 'update' is part of 'update_date'
        # Note: Keywords in strings will still be caught by our simple regex approach
        # This is acceptable for security - better to be overly cautious
    ]

    for query in safe_with_keyword_parts:
        is_safe, _ = is_query_safe(query)
        assert is_safe, f"Query should be safe (keyword in word): {query}"

    # Test that keywords in strings are still blocked (this is expected behavior)
    string_with_keywords = [
        "SELECT * FROM table WHERE description = 'CREATE something'",  # CREATE in string
    ]

    for query in string_with_keywords:
        is_safe, _ = is_query_safe(query)
        # This will be blocked, which is acceptable for security
        assert not is_safe, f"Query with keyword in string is blocked for safety: {query}"
