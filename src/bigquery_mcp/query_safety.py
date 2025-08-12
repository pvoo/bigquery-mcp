"""SQL query safety validation for BigQuery MCP Server."""

import re


def _has_multiple_statements_outside_quotes(sql: str) -> bool:
    """Detect multiple statements by counting semicolons outside quotes/backticks.

    Allows a single trailing semicolon but rejects if there's any content after a
    semicolon or if more than one semicolon exists outside of quotes.
    """
    in_single = False
    in_double = False
    in_backtick = False
    i = 0
    semicolon_count = 0
    length = len(sql)

    while i < length:
        ch = sql[i]

        # Handle single-quoted strings with doubled quotes inside ''
        if ch == "'" and not in_double and not in_backtick:
            # Toggle only if not an escaped doubled quote
            if i + 1 < length and sql[i + 1] == "'":
                i += 2
                continue
            in_single = not in_single
        elif ch == '"' and not in_single and not in_backtick:
            in_double = not in_double
        elif ch == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
        elif ch == ";" and not in_single and not in_double and not in_backtick:
            semicolon_count += 1
        i += 1

    if semicolon_count == 0:
        return False
    if semicolon_count >= 2:
        return True

    # Exactly one semicolon: allow only if it's trailing (ignoring whitespace)
    last_index = sql.rfind(";")
    return bool(sql[last_index + 1 :].strip())


def is_query_safe(query: str) -> tuple[bool, str]:
    """Check if SQL query is safe (read-only) and doesn't contain dangerous operations.

    This function validates that queries are read-only SELECT or WITH statements
    and don't contain keywords that could modify data or perform dangerous operations.
    Comments are stripped to prevent bypassing safety checks.

    Args:
        query: SQL query string to validate

    Returns:
        Tuple of (is_safe: bool, error_message: str)
        - If query is safe: (True, "")
        - If query is unsafe: (False, "Description of the safety violation")

    Examples:
        >>> is_query_safe("SELECT * FROM table")
        (True, "")

        >>> is_query_safe("DROP TABLE users")
        (False, "Query contains dangerous keyword 'DROP'. Only read-only SELECT queries are allowed.")

        >>> is_query_safe("SELECT * FROM table; -- DROP TABLE users")
        (True, "")  # Comments are stripped before validation
    """
    if not query or not query.strip():
        return False, "Empty query is not allowed."

    # Convert to uppercase for keyword checking and strip whitespace
    query_upper = query.upper().strip()

    # Remove SQL comments to prevent bypassing safety checks
    # Remove line comments (-- comment)
    query_upper = re.sub(r"--.*", "", query_upper)
    # Remove block comments (/* comment */)
    query_upper = re.sub(r"/\*.*?\*/", "", query_upper, flags=re.DOTALL)

    # Strip again after comment removal
    query_upper = query_upper.strip()

    if not query_upper:
        return False, "Query contains only comments, no actual SQL statement."

    # Validate query starts with allowed keywords
    # Must start with SELECT (for queries) or WITH (for CTEs)
    allowed_start_patterns = [
        r"^\s*SELECT\b",  # SELECT queries
        r"^\s*WITH\b",  # Common Table Expressions (CTEs)
    ]

    if not any(re.match(pattern, query_upper) for pattern in allowed_start_patterns):
        return False, (
            "Only SELECT and WITH queries are allowed for safety. "
            f"Query starts with: {query_upper.split()[0] if query_upper.split() else 'unknown'}"
        )

    # Reject multi-statement scripts while respecting quotes/backticks
    if _has_multiple_statements_outside_quotes(query_upper):
        return False, ("Multiple SQL statements are not allowed. Please execute one SELECT or WITH query at a time.")

    # Define dangerous keywords that modify data or perform system operations
    dangerous_keywords = [
        # Data modification
        "DELETE",
        "UPDATE",
        "INSERT",
        "MERGE",
        "TRUNCATE",
        # Schema modification
        "DROP",
        "CREATE",
        "ALTER",
        # Permission and security
        "GRANT",
        "REVOKE",
        # System operations
        "EXEC",
        "EXECUTE",
        "CALL",
        # Export operations (could be used for data exfiltration)
        "EXPORT",
    ]

    # Check for dangerous keywords at word boundaries
    # Using word boundaries (\b) ensures we don't match partial words
    for keyword in dangerous_keywords:
        if re.search(rf"\b{keyword}\b", query_upper):
            return False, (
                f"Query contains dangerous keyword '{keyword}'. Only read-only SELECT and WITH queries are allowed."
            )

    # Additional safety checks for specific BigQuery patterns

    # (No additional checks)

    # All safety checks passed
    return True, ""
