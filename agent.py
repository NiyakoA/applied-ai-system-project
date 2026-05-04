"""
Agentic debugging workflow powered by Groq.

The agent follows a plan → act → verify loop:
  1. Analyze the buggy code (check syntax, reproduce the error)
  2. Diagnose the root cause
  3. Apply a targeted fix
  4. Verify the fix by running the corrected code

Groq drives the loop autonomously via tool calling; we stop when it calls
apply_fix with a passing result or when max_iterations is reached.
"""

import json
import logging
import os
from typing import Optional

from groq import Groq

from tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert Python debugging agent. Systematically debug buggy Python code using tools.

Workflow:
1. ANALYZE  — Call check_syntax first, then run_code to reproduce the error.
2. DIAGNOSE — Read the output carefully and identify the root cause.
3. FIX      — Write a corrected version of the code.
4. VERIFY   — Call apply_fix; it runs the corrected code automatically.

Rules:
- Always reproduce the original error before proposing a fix.
- Call apply_fix only when you are confident in the fix.
- If apply_fix fails, diagnose the new error and try again.
- Keep fixes minimal — change only what is necessary.
"""


def run_debugging_agent(
    buggy_code: str,
    error_message: Optional[str] = None,
    model: str = "qwen/qwen3-32b",
    max_iterations: int = 12,
) -> dict:
    """
    Run the agentic debugging loop.

    Returns:
        steps       — list of dicts describing every agent action
        fixed_code  — the verified corrected code, or None
        explanation — agent's explanation of the bug and fix
        confidence  — agent's self-reported confidence (0.0–1.0), or None
        success     — True if a working fix was found
        iterations  — number of API calls made
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    steps: list[dict] = []
    fixed_code: Optional[str] = None
    explanation: str = ""
    confidence: Optional[float] = None

    user_message = f"Please debug this Python code:\n\n```python\n{buggy_code}\n```"
    if error_message and error_message.strip():
        user_message += (
            f"\n\nError observed when running it:\n```\n{error_message.strip()}\n```"
        )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    logger.info(
        "Debugging agent started (model=%s, code_len=%d)", model, len(buggy_code)
    )

    used_iterations = 0
    for iteration in range(max_iterations):
        used_iterations = iteration + 1
        logger.info("Iteration %d/%d", iteration + 1, max_iterations)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                max_tokens=4096,
            )
        except Exception as exc:
            logger.error("API error on iteration %d: %s", iteration + 1, exc)
            steps.append(
                {"type": "error", "content": f"API error: {exc}", "iteration": iteration + 1}
            )
            break

        choice = response.choices[0]
        message = choice.message
        logger.info("finish_reason=%s", choice.finish_reason)

        # Record any text the model produced
        if message.content and message.content.strip():
            steps.append(
                {"type": "analysis", "content": message.content, "iteration": iteration + 1}
            )

        # Add assistant turn to history
        assistant_msg: dict = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_msg)

        if not message.tool_calls or choice.finish_reason == "stop":
            logger.info("No tool calls — agent finished")
            break

        # Execute each tool call and append results
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            result = execute_tool(tc.function.name, args)

            steps.append(
                {
                    "type": "tool_call",
                    "tool": tc.function.name,
                    "input": args,
                    "result": result,
                    "iteration": iteration + 1,
                }
            )

            if tc.function.name == "apply_fix":
                explanation = args.get("explanation", "")
                confidence = result.get("confidence")
                if result.get("success"):
                    fixed_code = result.get("fixed_code") or args.get("fixed_code")
                    logger.info(
                        "Fix verified — stopping agent (confidence=%.2f)",
                        confidence if confidence is not None else -1,
                    )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                }
            )

        if fixed_code is not None:
            break

    if not explanation:
        for step in reversed(steps):
            if step["type"] == "analysis" and step["content"].strip():
                explanation = step["content"]
                break

    logger.info(
        "Agent done: success=%s, iterations=%d", fixed_code is not None, used_iterations
    )

    return {
        "steps": steps,
        "fixed_code": fixed_code,
        "explanation": explanation,
        "confidence": confidence,
        "success": fixed_code is not None,
        "iterations": used_iterations,
    }
