# AI Code Debugger Agent

DEMO VID: https://youtu.be/3cG1Ux-Jl6Y

An agentic AI system that autonomously diagnoses and fixes buggy Python code using Claude's tool-use loop. The agent plans its approach, acts by running real code, and verifies its own fix before reporting — no human in the loop required.

---

## Original Project (Modules 1-3): Game Glitch Investigator

The starting point for this course was the **Game Glitch Investigator** — a broken Streamlit number-guessing game. Its goals were to practice debugging, Streamlit session state, and test-driven development. The app had three concrete bugs: higher/lower hints were inverted, a show-hints checkbox made the game unplayable when unchecked, and the score was hidden from the player. After fixing those bugs and adding a test for string-typed secret numbers, all five pytest tests passed and the game ran correctly.

---

## What This Project Does and Why It Matters

Developers spend a significant portion of their time debugging — reading stack traces, forming hypotheses, applying fixes, and re-running code. This project automates that workflow. You paste broken Python code (and optionally the error message), click **Debug Code**, and an AI agent powered by Claude Opus 4.7 walks through the same steps a senior developer would:

1. Checks for syntax errors first (cheapest signal)
2. Runs the code to reproduce the error
3. Diagnoses the root cause
4. Applies a minimal, targeted fix
5. Verifies the corrected code runs without errors

The fixed code, an explanation of the bug, and a full step-by-step trace of everything the agent tried are shown in the UI.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Human Layer                                                 │
│  User pastes buggy code + optional error → clicks Debug Code │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP request
┌─────────────────────────▼────────────────────────────────────┐
│  UI Layer — app.py (Streamlit)                               │
│  • Input form  • Example selector  • Step-by-step trace      │
└─────────────────────────┬────────────────────────────────────┘
                          │ run_debugging_agent(buggy_code)
┌─────────────────────────▼────────────────────────────────────┐
│  Agentic Loop — agent.py                                     │
│  Plan → Act → Verify  (up to 12 iterations)                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Claude Opus 4.7  (claude-opus-4-7)                 │    │
│  │  • adaptive thinking  • effort: high                │    │
│  │  • system prompt cached across iterations           │    │
│  └──────┬───────────────────────────────────┬──────────┘    │
│         │ tool_use blocks                   │ tool_results  │
│  ┌──────▼───────────────────────────────────┴──────────┐    │
│  │  Tool Executor — tools.py                           │    │
│  │  check_syntax │ run_code │ apply_fix                │    │
│  └──────────────────────────┬───────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────┘
                              │ subprocess + tempfile
┌─────────────────────────────▼────────────────────────────────┐
│  Local Python Runtime                                        │
│  Isolated execution via subprocess.run, 10-second timeout    │
│  stdout / stderr / returncode returned to agent              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Testing & Reliability Layer                                 │
│  tests/test_tools.py  — 19 unit tests, no API required       │
│  tests/test_agent.py  — 5 integration tests, needs API key   │
│  logger_config.py     — file + stream logging, noisy libs    │
│                          suppressed, daily rotating log file │
└──────────────────────────────────────────────────────────────┘
```

**Data flow:** User input travels from the Streamlit form → `run_debugging_agent()` → Claude API → `execute_tool()` → local subprocess → results back up the same chain until the fix is verified or the iteration limit is reached.

**Human checkpoints:** The human provides the buggy code, optionally supplies the error message, and reviews the final explanation and corrected code. The UI also shows every tool call the agent made so the human can audit the reasoning.

---

## Setup Instructions

### Prerequisites

- Python 3.10 or later
- An Anthropic API key ([get one here](https://console.anthropic.com/settings/keys))

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/NiyakoA/applied-ai-system-project.git
cd applied-ai-system-project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
cp .env.example .env
# Open .env and replace the placeholder with your real key:
# ANTHROPIC_API_KEY=sk-ant-...

# 4. Run the app
python -m streamlit run app.py

# 5. (Optional) Run tests
pytest                     # unit tests only — no API key needed
pytest tests/test_agent.py # integration tests — requires API key
```

The app opens at `http://localhost:8501`. Choose a built-in example from the dropdown or paste your own code, then click **Debug Code**.

---

## Sample Interactions

### Example 1 — ZeroDivisionError

**Input code:**
```python
def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count  # Bug: crashes on an empty list

result = calculate_average([])
print(f"Average: {result}")
```

**Agent output (abbreviated):**
- `check_syntax` → valid
- `run_code` (reproducing original error) → `ZeroDivisionError: division by zero`
- `apply_fix` → verification: passed

**Explanation:**  
*The bug is in `calculate_average`: when called with an empty list, `len([])` returns 0 and the division `total / count` raises a ZeroDivisionError. The fix adds a guard that returns 0.0 (or raises a ValueError) when the list is empty.*

**Fixed code:**
```python
def calculate_average(numbers):
    if not numbers:
        return 0.0
    total = sum(numbers)
    count = len(numbers)
    return total / count

result = calculate_average([])
print(f"Average: {result}")
```

---

### Example 2 — NameError

**Input code:**
```python
def greet_user(name):
    message = f"Hello, {username}!"  # Bug: 'username' is undefined; should be 'name'
    return message

print(greet_user("Alice"))
```

**Agent output (abbreviated):**
- `check_syntax` → valid
- `run_code` (reproducing original error) → `NameError: name 'username' is not defined`
- `apply_fix` → verification: passed

**Explanation:**  
*Inside `greet_user`, the f-string references `username` but the parameter is named `name`. Replacing `username` with `name` fixes the NameError.*

**Fixed code:**
```python
def greet_user(name):
    message = f"Hello, {name}!"
    return message

print(greet_user("Alice"))
```

---

### Example 3 — Logic Error (off-by-one)

**Input code:**
```python
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
```

**Agent output (abbreviated):**
- `check_syntax` → valid
- `run_code` (reproducing original error) → prints `[0, 1, 1, 2]` (only 4 elements)
- `apply_fix` → verification: passed

**Explanation:**  
*The slice `fib[:n - 1]` returns one fewer element than requested. For `n=5`, it returns 4 elements instead of 5. The fix changes the slice to `fib[:n]` so the correct number of Fibonacci numbers is returned.*

**Fixed code:**
```python
def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i - 1] + fib[i - 2])

    return fib[:n]

print(fibonacci(5))
```

---

## Design Decisions

### Why a manual tool-use loop instead of a pre-built agent framework?

Using the Anthropic SDK's raw tool-use API makes the agent's behavior transparent and fully controllable. Every tool call is a Python function call I wrote — no hidden framework magic. This made testing, debugging, and explaining the system much easier for a course project.

### Why only three tools?

More tools mean more decision surface for the model. Three tools (`check_syntax`, `run_code`, `apply_fix`) map directly to the three steps of any debugging session: detect, reproduce, fix. Keeping the surface small forces Claude to focus and reduces the chance of the agent going off-track.

### Why `apply_fix` auto-verifies instead of returning immediately?

Making `apply_fix` both submit the fix and verify it runs closes the loop inside the tool. The agent cannot claim success without the fix actually passing. This is a guardrail — the agent is structurally prevented from hallucinating a working fix.

### Why subprocess + tempfile for code execution?

Running untrusted code in a subprocess isolates it from the host process. The 10-second timeout prevents infinite loops from hanging the app. Using a tempfile avoids eval/exec entirely, which would share the host process's scope and namespace.

### Why prompt caching on the system prompt?

The system prompt is the same on every iteration of the loop. Marking it with `cache_control: ephemeral` means Anthropic caches it server-side, so repeated API calls within the same session do not re-tokenize and re-price the system prompt. On a 12-iteration debugging session this can cut token costs by 30–50%.

### Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| Manual loop | Full transparency, easy to test | More boilerplate than a framework |
| 3 tools only | Focused, predictable behavior | Can't write to disk or search docs |
| apply_fix auto-verifies | Structural correctness guarantee | Agent can't stage a speculative fix |
| 10-second subprocess timeout | Prevents hangs | Slow code won't run long enough to succeed |
| Subprocess isolation | Safe execution | Slight overhead per run (~50 ms) |

---

## Testing Summary

**22/22 unit tests pass with no API key. 5/5 integration tests pass with a valid key. Confidence scores from live runs averaged 0.87 across all five example bugs; the agent scored ≥ 0.90 on clear runtime errors (ZeroDivisionError, NameError) and 0.75–0.80 on the off-by-one logic bug where the root cause was less obvious from the traceback alone.**

### How reliability is measured

This project uses four complementary reliability signals:

| Method | Implementation | What it catches |
|--------|---------------|-----------------|
| **Automated unit tests** | `tests/test_tools.py` — 22 tests, no API key | Tool correctness, edge cases, timeout, clamping |
| **Integration tests** | `tests/test_agent.py` — 5 tests, live API | End-to-end agent behavior, runnable output |
| **Confidence scoring** | Claude self-reports 0.0–1.0 on every `apply_fix` call | Model uncertainty; displayed in UI with color coding |
| **Structured logging** | `logger_config.py` — file + stream, daily rotation | Every tool call, iteration count, verification result |

### Unit test results (no API key required)

```
tests/test_tools.py::TestRunCode::test_success                   PASSED
tests/test_tools.py::TestRunCode::test_runtime_error             PASSED
tests/test_tools.py::TestRunCode::test_zero_division             PASSED
tests/test_tools.py::TestRunCode::test_multiline_output          PASSED
tests/test_tools.py::TestRunCode::test_timeout                   PASSED
tests/test_tools.py::TestRunCode::test_label_preserved           PASSED
tests/test_tools.py::TestCheckSyntax::test_valid_code            PASSED
tests/test_tools.py::TestCheckSyntax::test_syntax_error          PASSED
tests/test_tools.py::TestCheckSyntax::test_empty_code            PASSED
tests/test_tools.py::TestCheckSyntax::test_missing_colon         PASSED
tests/test_tools.py::TestCheckSyntax::test_valid_function        PASSED
tests/test_tools.py::TestApplyFix::test_working_fix              PASSED
tests/test_tools.py::TestApplyFix::test_syntax_error_in_fix      PASSED
tests/test_tools.py::TestApplyFix::test_runtime_error_in_fix     PASSED
tests/test_tools.py::TestApplyFix::test_explanation_preserved    PASSED
tests/test_tools.py::TestApplyFix::test_confidence_preserved     PASSED
tests/test_tools.py::TestApplyFix::test_confidence_clamped       PASSED
tests/test_tools.py::TestApplyFix::test_confidence_in_syntax_error PASSED
tests/test_tools.py::TestExecuteTool::test_dispatch_run_code     PASSED
tests/test_tools.py::TestExecuteTool::test_dispatch_check_syntax PASSED
tests/test_tools.py::TestExecuteTool::test_dispatch_apply_fix    PASSED
tests/test_tools.py::TestExecuteTool::test_unknown_tool          PASSED

22 passed in 1.64s
```

### Integration test coverage (requires API key)

| Test | What it verifies |
|------|-----------------|
| `test_fixes_zero_division` | Agent finds and fixes a crash bug |
| `test_fixes_name_error` | Agent identifies an undefined variable |
| `test_fixed_code_is_runnable` | Fixed code actually runs via subprocess — not just syntactically valid |
| `test_agent_reports_iterations` | `iterations >= 1` in every run |
| `test_agent_steps_populated` | At least one `tool_call` step exists, proving Claude used tools |

### Confidence scoring

Every `apply_fix` call requires Claude to report a confidence score between 0.0 and 1.0. The score is:

- Displayed in the UI in green (≥ 85%), orange (60–84%), or red (< 60%)
- Logged to the daily log file alongside the verification result
- Tested for range clamping (values outside 0–1 are clipped)

A low score is a signal to review the fix carefully even if the code runs — Claude may have addressed the symptom rather than the root cause.

### What worked

- The three-tool design kept the agent reliably on track. In every test run it followed the check → reproduce → fix → verify sequence without wandering.
- `apply_fix` auto-verification caught cases where the agent was overconfident and the fix still had a runtime error, triggering another iteration automatically.
- The timeout guardrail worked in `test_timeout` — infinite loops are caught in 1 second without hanging the suite.

### What didn't work (and what I learned)

- `test_fixed_code_is_runnable` occasionally surfaces logic bugs where the agent's fix is syntactically valid but semantically wrong — `apply_fix` returns `failed` and the test catches it correctly. Verifying "runs without exception" is not the same as verifying "produces the right output."
- Early versions of `agent.py` didn't handle `stop_reason == "end_turn"` with no tool calls, causing the loop to over-iterate. Adding the explicit break fixed this.
- Confidence scores on logic errors (off-by-one, wrong slice index) averaged lower than on runtime errors — the model knows when it is less certain, which is a useful signal rather than a flaw.

---

## Responsible AI

### Limitations and biases

The most significant limitation is how the agent defines "correct." A fix passes if the code runs without raising an exception — not if it produces the right answer. The off-by-one Fibonacci bug illustrates this: a fix that returns an empty list instead of crashing would pass verification even though it is wrong. The system has no way to know what output the user actually expects without a test suite or specification to check against.

The agent is also Python-only. The tools use `ast.parse` and `sys.executable`, so any code in another language gets misdiagnosed or silently fails. There is no warning about this in the UI, which could mislead a user who pastes a JavaScript or shell snippet.

Claude's training data skews heavily toward well-structured, open-source Python. This creates a bias toward common patterns: it handles a ZeroDivisionError more fluently than domain-specific logic errors in scientific or financial code, where the conventions and intent are less represented in its training. The confidence score partially surfaces this — it tends to be lower on unfamiliar problem domains — but it does not eliminate the underlying gap.

Finally, the subprocess timeout of 10 seconds is a practical guardrail, not a semantic one. Code that genuinely needs more than 10 seconds to run (a database migration, a large file parse) will fail verification and the agent will incorrectly conclude the fix did not work.

### Could this AI be misused?

Yes. The most direct misuse is code execution: a user can paste a script that deletes files, exfiltrates environment variables, or spawns background processes, and the agent will execute it without question via `subprocess.run`. The current mitigations are:

- **Subprocess isolation**: the code runs in a child process, not `eval()` in the host process, so it cannot access local variables or the Anthropic client object directly
- **10-second timeout**: prevents persistent background activity within a single run
- **Tempfile cleanup**: the script file is deleted after each execution

What is *not* protected: network access, filesystem writes outside the temp directory, and reading environment variables (`ANTHROPIC_API_KEY` is accessible from a subprocess on the same machine). For a production deployment, additional hardening would be needed — running the subprocess in a container with no network, a read-only filesystem mount, and a seccomp profile that blocks dangerous syscalls. In the current form this tool is appropriate for a local development environment where the user is also the person pasting the code.

### What surprised me during testing

The confidence score turned out to be genuinely informative rather than just decorative. I expected the model to report high confidence on almost every call — optimism bias is a known LLM tendency. Instead, confidence scores on logic errors (off-by-one, wrong slice index) were measurably lower than on runtime errors with clear tracebacks. The model appeared to distinguish between "I can see exactly what line caused this" (high confidence) and "this is a semantic issue where I am reconstructing intent" (lower confidence). That distinction was not designed in — it emerged from asking Claude to reason about its own certainty.

The other surprise was that the agent occasionally explained the fix correctly but described the root cause incorrectly in the explanation field. The code it produced was right, but the reasoning it stated to the user was a plausible-sounding alternative theory. This is a real limitation for a debugging tool: the user might learn the wrong lesson about why their code broke.

### Collaboration with AI during this project

**Helpful suggestion:** When designing the tool definitions, Claude suggested keeping `apply_fix` as a terminal tool that runs verification internally, rather than having a separate `verify_fix` tool the agent would have to call afterward. This was the right call. It made the loop self-closing — the agent physically cannot report success without the code passing — and it simplified both the agent loop logic and the tests. I had initially sketched a four-tool design; the consolidated three-tool version was cleaner and more reliable.

**Flawed suggestion:** During an early iteration, Claude suggested using `exec(compile(code, "<string>", "exec"))` inside the host process as a "simpler" alternative to spawning a subprocess. This would have been a serious security regression: `exec` in the host process shares the global namespace, can access the `anthropic` client object and the API key, and has no timeout mechanism. I rejected it and kept the `subprocess.run` + tempfile approach. The lesson was that AI suggestions for "simpler" implementations in security-sensitive contexts need skepticism — simplicity and safety can be in direct conflict, and the model does not always flag that tension unprompted.

---

## Reflection

This project taught me that building an agentic AI system is less about prompting and more about **structure**. The system prompt is short — a few sentences — because the tools themselves encode the workflow. An agent that *must* call `check_syntax` before `run_code`, and *must* call `apply_fix` to terminate, is structurally guided, not just instructed. That distinction matters: instructions can be ignored, but structure cannot.

I also learned that safe code execution is a first-class design concern, not an afterthought. Using `subprocess.run` with a tempfile and a timeout felt like extra complexity at first, but it's what makes the system trustworthy enough to run arbitrary user code without fear. The guardrail is invisible when everything works and essential when something goes wrong.

The hardest part was not the AI integration — the Anthropic SDK made that straightforward — but deciding what the agent *should not* be able to do. Limiting the tool surface to three functions forced clarity about what the agent's job actually is: diagnose and fix, nothing more.

Finally, watching the agent work through a multi-step debugging session reinforced that modern LLMs are genuinely useful as reasoning engines when given the right scaffolding. The agent doesn't just pattern-match — it reproduces the error, reads the output, and then forms a hypothesis. That's the same process a developer uses. The difference is that it happens in seconds and the reasoning is fully logged and auditable.
