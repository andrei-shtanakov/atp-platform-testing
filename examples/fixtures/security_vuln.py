"""Module with INTENTIONAL security vulnerabilities for testing code review agents.

WARNING: This file contains deliberately insecure code.
It is a TEST FIXTURE — NOT production code.
Used to verify that a code review agent correctly identifies vulnerabilities.
"""

import sqlite3
import subprocess


# Vulnerability 1: SQL Injection
def get_user(username: str) -> dict | None:
    """Get user by username from database."""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # DELIBERATELY VULNERABLE: string formatting in SQL query
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    return row


# Vulnerability 2: Command Injection
def run_diagnostic(host: str) -> str:
    """Run network diagnostic on a host."""
    # DELIBERATELY VULNERABLE: shell=True with user input
    result = subprocess.run(
        f"ping -c 1 {host}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


# Vulnerability 3: Hardcoded credentials (FAKE values for testing)
DATABASE_URL = "postgresql://admin:password123@prod-db.internal:5432/app"
API_SECRET = "sk-live-FAKE-KEY-FOR-TESTING-ONLY"


# Vulnerability 4: Path traversal
def read_user_file(filename: str) -> str:
    """Read a file from the user uploads directory."""
    # DELIBERATELY VULNERABLE: no path sanitization
    filepath = f"/var/uploads/{filename}"
    with open(filepath) as f:
        return f.read()


# Vulnerability 5: Insecure deserialization
# NOTE: This is an intentional test fixture to verify that
# the code review agent flags pickle usage with untrusted data.
import pickle  # noqa: E402


def load_session(data: bytes) -> dict:
    """Load user session from serialized data."""
    # DELIBERATELY VULNERABLE: pickle.loads with untrusted data
    # A good reviewer should flag this as a critical security issue
    return pickle.loads(data)  # noqa: S301
