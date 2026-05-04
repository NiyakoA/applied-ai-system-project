"""
AI Code Debugger — Streamlit UI

An agentic AI that autonomously plans, acts, and verifies fixes
for buggy Python code using Gemini's function-calling loop.
"""

import os

import streamlit as st
from dotenv import load_dotenv

from agent import run_debugging_agent
from logger_config import setup_logging

load_dotenv()
setup_logging()

# ---------------------------------------------------------------------------
# Example buggy programs
# ---------------------------------------------------------------------------
EXAMPLES: dict[str, str] = {
    "ZeroDivisionError": """\
def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count  # Bug: crashes on an empty list

result = calculate_average([])
print(f"Average: {result}")
""",
    "NameError": """\
def greet_user(name):
    message = f"Hello, {username}!"  # Bug: 'username' is undefined; should be 'name'
    return message

print(greet_user("Alice"))
""",
    "Logic Error (off-by-one)": """\
def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i - 1] + fib[i - 2])

    return fib[:n - 1]  # Bug: slices one element too few

# Expected: [0, 1, 1, 2, 3]
print(fibonacci(5))
""",
    "TypeError": """\
def multiply_items(items, factor):
    return [item * factor for item in items]

numbers = "123"          # Bug: should be [1, 2, 3], not a string
result = multiply_items(numbers, 2)
print(result)
""",
    "IndexError": """\
def get_second_largest(numbers):
    sorted_nums = sorted(numbers)
    return sorted_nums[-2]  # Bug: crashes when the list has fewer than 2 elements

print(get_second_largest([42]))
""",
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Code Debugger Agent",
    page_icon="🐛",
    layout="wide",
)

st.title("🐛 AI Code Debugger Agent")
st.caption(
    "An agentic AI that **plans → acts → verifies** fixes for buggy Python code. "
    "Powered by Groq (Llama 3.3) with tool calling."
)

# ---------------------------------------------------------------------------
# API key guard
# ---------------------------------------------------------------------------
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("**GROQ_API_KEY not set.** Create a `.env` file with:")
    st.code("GROQ_API_KEY=gsk_...")
    st.stop()

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Input")

    example_choice = st.selectbox(
        "Load a built-in example:",
        ["— choose one —"] + list(EXAMPLES.keys()),
    )

    default_code = (
        EXAMPLES.get(example_choice, "")
        if example_choice != "— choose one —"
        else ""
    )

    buggy_code = st.text_area(
        "Buggy Python Code",
        value=default_code,
        height=260,
        placeholder="Paste your broken Python code here…",
    )

    error_message = st.text_area(
        "Error / Traceback (optional)",
        height=110,
        placeholder="Paste the error or traceback you observe when running the code…",
    )

    run_btn = st.button(
        "Debug Code",
        type="primary",
        disabled=not buggy_code.strip(),
        use_container_width=True,
    )

    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Gemini checks syntax and reproduces the error with tools\n"
        "2. Gemini diagnoses the root cause\n"
        "3. Groq applies a fix and verifies it runs successfully\n"
        "4. The corrected code and explanation are shown on the right"
    )

# ---------------------------------------------------------------------------
# Run the agent
# ---------------------------------------------------------------------------
with right:
    st.subheader("Results")

    if run_btn and buggy_code.strip():
        status = st.status("Agent is working…", expanded=True)

        try:
            with status:
                result = run_debugging_agent(
                    buggy_code=buggy_code,
                    error_message=error_message or None,
                )
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.stop()

        if result["success"]:
            status.update(
                label=f"Bug fixed in {result['iterations']} iteration(s)!",
                state="complete",
            )
            st.success("Fix verified — the corrected code runs without errors.")
        else:
            status.update(
                label=(
                    f"Could not find a verified fix "
                    f"({result['iterations']} iteration(s) used)."
                ),
                state="error",
            )
            st.warning(
                "The agent could not produce a verified fix. "
                "See the steps below for what it tried."
            )

        # Confidence score
        conf = result.get("confidence")
        if conf is not None:
            if conf >= 0.85:
                label = f"Agent confidence: {conf:.0%} — high"
                color = "green"
            elif conf >= 0.60:
                label = f"Agent confidence: {conf:.0%} — moderate"
                color = "orange"
            else:
                label = f"Agent confidence: {conf:.0%} — low (review carefully)"
                color = "red"
            st.markdown(
                f'<p style="color:{color}; font-weight:600">{label}</p>',
                unsafe_allow_html=True,
            )

        # Explanation
        if result["explanation"]:
            st.markdown("### Explanation")
            st.markdown(result["explanation"])

        # Fixed code
        if result["fixed_code"]:
            st.markdown("### Fixed Code")
            st.code(result["fixed_code"], language="python")

        # Step-by-step breakdown
        st.markdown("### Agent Steps")

        by_iteration: dict[int, list[dict]] = {}
        for step in result["steps"]:
            it = step.get("iteration", 0)
            by_iteration.setdefault(it, []).append(step)

        for it, steps in sorted(by_iteration.items()):
            with st.expander(f"Iteration {it}", expanded=(it == 1)):
                for step in steps:
                    stype = step["type"]

                    if stype == "analysis":
                        st.markdown(step["content"])

                    elif stype == "tool_call":
                        tool = step["tool"]
                        res = step["result"]
                        ok = res.get("success", res.get("valid", False))
                        icon = "✅" if ok else "❌"

                        if tool == "check_syntax":
                            msg = (
                                "No syntax errors"
                                if ok
                                else f"Syntax error: {res.get('error', '')}"
                            )
                            st.write(f"{icon} **check_syntax** — {msg}")

                        elif tool == "run_code":
                            label = step["input"].get("label", "run")
                            st.write(f"{icon} **run_code** ({label})")
                            if res.get("stdout"):
                                st.code(res["stdout"][:500], language="text")
                            if res.get("stderr"):
                                st.code(res["stderr"][:500], language="text")
                            if res.get("error"):
                                st.code(res["error"], language="text")

                        elif tool == "apply_fix":
                            verification = res.get("verification", "unknown")
                            conf_val = res.get("confidence")
                            conf_str = f" | confidence: {conf_val:.0%}" if conf_val is not None else ""
                            st.write(
                                f"{icon} **apply_fix** — verification: {verification}{conf_str}"
                            )
                            if res.get("stderr"):
                                st.code(res["stderr"][:400], language="text")
                            if res.get("error"):
                                st.code(res["error"], language="text")

                    elif stype == "error":
                        st.error(step["content"])
    else:
        st.info(
            "Choose an example or paste your own code on the left, "
            "then click **Debug Code** to start."
        )
