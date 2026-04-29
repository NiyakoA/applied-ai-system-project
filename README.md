# 🎮 Game Glitch Investigator: The Impossible Guesser

## 🚨 The Situation

You asked an AI to build a simple "Number Guessing Game" using Streamlit.
It wrote the code, ran away, and now the game is unplayable. 

- You can't win.
- The hints lie to you.
- The secret number seems to have commitment issues.

## 🛠️ Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the broken app: `python -m streamlit run app.py`

## 🕵️‍♂️ Your Mission

1. **Play the game.** Open the "Developer Debug Info" tab in the app to see the secret number. Try to win.
2. **Find the State Bug.** Why does the secret number change every time you click "Submit"? Ask ChatGPT: *"How do I keep a variable from resetting in Streamlit when I click a button?"*
3. **Fix the Logic.** The hints ("Higher/Lower") are wrong. Fix them.
4. **Refactor & Test.** - Move the logic into `logic_utils.py`.
   - Run `pytest` in your terminal.
   - Keep fixing until all tests pass!
5. **Toggle Hints.** Add a sidebar checkbox so players can turn the higher/lower hints on or off. The game should still track outcomes and score even when hints are hidden.

## 📝 Document Your Experience

- Describe the game's purpose.
The game is a number guessing game where players try to guess a secret number within a range, receiving hints on whether their guess is higher or lower, and earning scores based on attempts.
- Detail which bugs you found.
The main bugs were: inaccurate hints due to string conversion on even attempts, the hint button making the game unplayable when disabled, and the score not being prominently displayed.
- Explain what fixes you applied.
I removed the string conversion logic to ensure numerical comparison, eliminated the show_hints checkbox to always display hints, added a visible score display, and added a test case for string secret handling.

## 📸 Demo

> **Note:** Add a screenshot of the fixed game running in Streamlit here (showing accurate hints and visible score).

### pytest Results

All 5 tests passing:

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.3.5, pluggy-1.5.0
rootdir: ai110-module1show-gameglitchinvestigator-starter
plugins: Faker-38.2.0
collecting ... collected 5 items

tests/test_game_logic.py::test_winning_guess PASSED                      [ 20%]
tests/test_game_logic.py::test_guess_too_high PASSED                     [ 40%]
tests/test_game_logic.py::test_guess_too_low PASSED                      [ 60%]
tests/test_game_logic.py::test_hint_toggle_off PASSED                    [ 80%]
tests/test_game_logic.py::test_check_guess_with_string_secret PASSED     [100%]

============================== 5 passed in 0.19s ==============================
```

## 🚀 Stretch Features

- [ ] [If you choose to complete Challenge 4, insert a screenshot of your Enhanced Game UI here]
