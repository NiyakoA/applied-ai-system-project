"""Unit tests for tools.py — no API calls required."""

import pytest
from tools import run_code, check_syntax, apply_fix, execute_tool


# ---------------------------------------------------------------------------
# run_code
# ---------------------------------------------------------------------------

class TestRunCode:
    def test_success(self):
        r = run_code("print('hello')", label="test")
        assert r["success"]
        assert "hello" in r["stdout"]
        assert r["returncode"] == 0

    def test_runtime_error(self):
        r = run_code("raise ValueError('boom')", label="test error")
        assert not r["success"]
        assert "ValueError" in r["stderr"]
        assert r["returncode"] != 0

    def test_zero_division(self):
        r = run_code("x = 1 / 0", label="zero div")
        assert not r["success"]
        assert "ZeroDivisionError" in r["stderr"]

    def test_multiline_output(self):
        code = "for i in range(3):\n    print(i)"
        r = run_code(code, label="multiline")
        assert r["success"]
        assert "0" in r["stdout"]
        assert "2" in r["stdout"]

    def test_timeout(self):
        r = run_code("import time; time.sleep(999)", label="timeout test", timeout=1)
        assert not r["success"]
        assert "timed out" in r.get("error", "").lower()

    def test_label_preserved(self):
        r = run_code("x = 1", label="my label")
        assert r["label"] == "my label"


# ---------------------------------------------------------------------------
# check_syntax
# ---------------------------------------------------------------------------

class TestCheckSyntax:
    def test_valid_code(self):
        r = check_syntax("x = 1 + 2\nprint(x)")
        assert r["valid"]
        assert r["error"] is None

    def test_syntax_error(self):
        r = check_syntax("def foo(\n    pass")
        assert not r["valid"]
        assert r["error"] is not None
        assert "line" in r

    def test_empty_code(self):
        r = check_syntax("")
        assert r["valid"]

    def test_missing_colon(self):
        r = check_syntax("if True\n    pass")
        assert not r["valid"]

    def test_valid_function(self):
        code = "def add(a, b):\n    return a + b\nprint(add(1, 2))"
        r = check_syntax(code)
        assert r["valid"]


# ---------------------------------------------------------------------------
# apply_fix
# ---------------------------------------------------------------------------

class TestApplyFix:
    def test_working_fix(self):
        code = "x = 1\nprint(x)"
        r = apply_fix(fixed_code=code, explanation="Just printing")
        assert r["success"]
        assert r["verification"] == "passed"
        assert r["fixed_code"] == code

    def test_syntax_error_in_fix(self):
        bad = "def foo(\n    pass"
        r = apply_fix(fixed_code=bad, explanation="broken")
        assert not r["success"]
        assert r["verification"] == "syntax_error"

    def test_runtime_error_in_fix(self):
        code = "raise RuntimeError('still broken')"
        r = apply_fix(fixed_code=code, explanation="wrong fix")
        assert not r["success"]
        assert r["verification"] == "failed"

    def test_explanation_preserved(self):
        code = "print('ok')"
        r = apply_fix(fixed_code=code, explanation="my explanation")
        assert r["explanation"] == "my explanation"

    def test_confidence_preserved(self):
        code = "print('ok')"
        r = apply_fix(fixed_code=code, explanation="e", confidence=0.9)
        assert r["confidence"] == pytest.approx(0.9)

    def test_confidence_clamped(self):
        code = "print('ok')"
        r = apply_fix(fixed_code=code, explanation="e", confidence=1.5)
        assert r["confidence"] <= 1.0
        r2 = apply_fix(fixed_code=code, explanation="e", confidence=-0.3)
        assert r2["confidence"] >= 0.0

    def test_confidence_in_syntax_error(self):
        bad = "def foo(\n    pass"
        r = apply_fix(fixed_code=bad, explanation="broken", confidence=0.4)
        assert "confidence" in r
        assert r["confidence"] == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# execute_tool dispatcher
# ---------------------------------------------------------------------------

class TestExecuteTool:
    def test_dispatch_run_code(self):
        r = execute_tool("run_code", {"code": "print(1)", "label": "x"})
        assert r["success"]

    def test_dispatch_check_syntax(self):
        r = execute_tool("check_syntax", {"code": "x = 1"})
        assert r["valid"]

    def test_dispatch_apply_fix(self):
        r = execute_tool(
            "apply_fix",
            {"fixed_code": "print('hi')", "explanation": "e", "confidence": 0.95},
        )
        assert r["success"]
        assert r["confidence"] == pytest.approx(0.95)

    def test_unknown_tool(self):
        r = execute_tool("nonexistent_tool", {})
        assert "error" in r
        assert "Unknown tool" in r["error"]
