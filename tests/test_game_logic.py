from logic_utils import check_guess

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    result = check_guess(50, 50)
    assert result[0] == "Win"
    assert result[1] == "🎉 Correct!"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    result = check_guess(60, 50)
    assert result[0] == "Too High"
    assert result[1] == "📉 Go LOWER!"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    result = check_guess(40, 50)
    assert result[0] == "Too Low"
    assert result[1] == "📈 Go HIGHER!"


def test_hint_toggle_off():
    # When hints are disabled the outcome should still be correct but
    # the message returned by the helper is an empty string.
    from logic_utils import check_guess_with_hints

    outcome, message = check_guess_with_hints(60, 50, show_hints=False)
    assert outcome == "Too High"
    assert message == ""

    # turning hints back on restores the normal text
    outcome2, message2 = check_guess_with_hints(60, 50, show_hints=True)
    assert outcome2 == "Too High"
    assert message2 == "📉 Go LOWER!"


def test_check_guess_with_string_secret():
    # Test that check_guess handles string secrets correctly (targets the bug where secret was converted to str on even attempts) - FIX: Added this test as AI suggested to verify the string handling logic
    result = check_guess(60, "50")
    assert result[0] == "Too High"
    assert result[1] == "📉 Go LOWER!"

    result2 = check_guess(40, "50")
    assert result2[0] == "Too Low"
    assert result2[1] == "📈 Go HIGHER!"
