import subprocess
import sys
import ast
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

# Tool definitions in OpenAI/Groq function-calling format.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": (
                "Execute Python code in a subprocess and return stdout, stderr, and exit code. "
                "Use this to reproduce the original error or to test a proposed fix."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute"
                    },
                    "label": {
                        "type": "string",
                        "description": "Short label for this run, e.g. 'reproducing original error'"
                    }
                },
                "required": ["code", "label"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_syntax",
            "description": (
                "Check Python code for syntax errors without executing it. "
                "Returns whether the code parses successfully."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to check for syntax errors"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_fix",
            "description": (
                "Submit the final corrected code. This will verify the fix works by running it. "
                "Only call this when you are confident the fix is correct."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fixed_code": {
                        "type": "string",
                        "description": "The complete corrected Python code"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Clear explanation of what was wrong and exactly what you changed"
                    },
                    "confidence": {
                        "type": "number",
                        "description": (
                            "Your confidence that this fix is correct, from 0.0 (uncertain) "
                            "to 1.0 (certain)."
                        )
                    }
                },
                "required": ["fixed_code", "explanation", "confidence"]
            }
        }
    }
]


def run_code(code: str, label: str = "code execution", timeout: int = 10) -> dict:
    """Execute Python code safely with a timeout."""
    logger.info("run_code: %s", label)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "success": proc.returncode == 0,
            "label": label,
        }
        logger.info("run_code finished: returncode=%d", proc.returncode)
        return result
    except subprocess.TimeoutExpired:
        logger.warning("run_code timed out after %ds", timeout)
        return {
            "error": f"Execution timed out after {timeout} seconds",
            "success": False,
            "label": label,
        }
    except Exception as exc:
        logger.error("run_code exception: %s", exc)
        return {"error": str(exc), "success": False, "label": label}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def check_syntax(code: str) -> dict:
    """Check Python code for syntax errors without executing it."""
    logger.info("check_syntax called")
    try:
        ast.parse(code)
        logger.info("check_syntax: valid")
        return {"valid": True, "error": None}
    except SyntaxError as exc:
        logger.info("check_syntax: SyntaxError at line %s", exc.lineno)
        return {
            "valid": False,
            "error": str(exc),
            "line": exc.lineno,
            "offset": exc.offset,
            "text": exc.text,
        }


def apply_fix(fixed_code: str, explanation: str, confidence: float = 1.0) -> dict:
    """Verify the fix by checking syntax then running the code."""
    confidence = max(0.0, min(1.0, float(confidence)))
    logger.info("apply_fix: verifying fix (confidence=%.2f)", confidence)

    syntax = check_syntax(fixed_code)
    if not syntax["valid"]:
        logger.info("apply_fix: syntax error in fixed code")
        return {
            "success": False,
            "verification": "syntax_error",
            "error": syntax["error"],
            "fixed_code": fixed_code,
            "explanation": explanation,
            "confidence": confidence,
        }

    run_result = run_code(fixed_code, label="verifying fix")
    success = run_result.get("success", False)
    logger.info(
        "apply_fix: verification %s (confidence=%.2f)",
        "passed" if success else "failed",
        confidence,
    )

    return {
        "success": success,
        "verification": "passed" if success else "failed",
        "stdout": run_result.get("stdout", ""),
        "stderr": run_result.get("stderr", ""),
        "returncode": run_result.get("returncode"),
        "fixed_code": fixed_code,
        "explanation": explanation,
        "confidence": confidence,
        "error": run_result.get("error"),
    }


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Dispatch a tool call by name."""
    logger.info("execute_tool: %s", tool_name)
    if tool_name == "run_code":
        return run_code(
            code=tool_input["code"],
            label=tool_input.get("label", "code execution"),
        )
    if tool_name == "check_syntax":
        return check_syntax(code=tool_input["code"])
    if tool_name == "apply_fix":
        return apply_fix(
            fixed_code=tool_input["fixed_code"],
            explanation=tool_input["explanation"],
            confidence=tool_input.get("confidence", 1.0),
        )
    logger.warning("execute_tool: unknown tool '%s'", tool_name)
    return {"error": f"Unknown tool: {tool_name}"}
