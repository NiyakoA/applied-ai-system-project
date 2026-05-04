"""
Integration tests for the agentic debugging workflow.

These tests call the real Gemini API and are skipped automatically
when GOOGLE_API_KEY is not set.
"""

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY is not set — skipping live API tests",
)


def _run(buggy_code: str, error_msg: str = "") -> dict:
    from agent import run_debugging_agent

    return run_debugging_agent(
        buggy_code=buggy_code,
        error_message=error_msg or None,
    )


class TestAgentFixesSimpleBugs:
    def test_fixes_zero_division(self):
        code = """\
def divide(a, b):
    return a / b

print(divide(10, 0))
"""
        r = _run(code)
        assert r["success"], f"Agent failed. Steps: {r['steps']}"
        assert r["fixed_code"] is not None
        assert r["explanation"]
        assert r["iterations"] >= 1

    def test_fixes_name_error(self):
        code = """\
def greet(name):
    return f"Hello, {username}!"

print(greet("Alice"))
"""
        r = _run(code)
        assert r["success"], f"Agent failed. Steps: {r['steps']}"
        assert r["fixed_code"] is not None

    def test_fixed_code_is_runnable(self):
        """The fixed_code returned by the agent must actually run without errors."""
        import subprocess, sys, tempfile

        code = """\
numbers = [3, 1, 2]
numbers.sort()
print(numbers[10])  # IndexError: list index out of range
"""
        r = _run(code)
        assert r["success"], "Agent did not find a fix"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(r["fixed_code"])
            tmp = f.name

        try:
            proc = subprocess.run(
                [sys.executable, tmp], capture_output=True, text=True, timeout=10
            )
            assert proc.returncode == 0, (
                f"Fixed code still fails:\n{proc.stderr}"
            )
        finally:
            os.unlink(tmp)

    def test_agent_reports_iterations(self):
        code = "print(undefined_variable)"
        r = _run(code)
        assert r["iterations"] >= 1

    def test_agent_steps_populated(self):
        code = "1/0"
        r = _run(code)
        assert len(r["steps"]) > 0
        types = {s["type"] for s in r["steps"]}
        assert "tool_call" in types
