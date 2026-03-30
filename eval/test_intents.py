"""
Intent classification evaluation suite.

Measures the agent's accuracy at mapping natural language commands
to the correct tool across languages and phrasings.

Run with:
    pytest eval/ -v
    pytest eval/ -v --tb=short   # less verbose on failures
"""
import time
from typing import Optional

import pytest

from agent.runner import execute_agent

# ---------------------------------------------------------------------------
# Test cases: (message, expected_action, description)
# ---------------------------------------------------------------------------

INTENT_CASES = [
    # --- start_cleaning ---
    ("começa a limpar", "start_cleaning", "PT: direct command"),
    ("inicia a limpeza", "start_cleaning", "PT: synonym"),
    ("pode limpar a casa?", "start_cleaning", "PT: polite request"),
    ("start cleaning", "start_cleaning", "EN: direct command"),
    ("vacuum the house", "start_cleaning", "EN: synonym"),
    ("begin cleaning please", "start_cleaning", "EN: polite"),

    # --- stop_cleaning ---
    ("para o robô", "stop_cleaning", "PT: direct"),
    ("pausa a limpeza", "stop_cleaning", "PT: synonym"),
    ("stop the robot", "stop_cleaning", "EN: direct"),
    ("pause cleaning", "stop_cleaning", "EN: synonym"),
    ("halt", "stop_cleaning", "EN: terse"),

    # --- return_to_base ---
    ("volta para a base", "return_to_base", "PT: direct"),
    ("manda ele carregar", "return_to_base", "PT: indirect"),
    ("return to base", "return_to_base", "EN: direct"),
    ("go back to dock", "return_to_base", "EN: synonym"),
    ("charge the robot", "return_to_base", "EN: semantic"),

    # --- locate_robot ---
    ("onde está o robô?", "locate_robot", "PT: question"),
    ("localiza o robô", "locate_robot", "PT: direct"),
    ("where is the robot?", "locate_robot", "EN: question"),
    ("find the vacuum", "locate_robot", "EN: synonym"),
    ("locate robot", "locate_robot", "EN: terse"),

    # --- set_clean_mode ---
    ("modo espiral", "set_clean_mode", "PT: mode name"),
    ("limpa em modo aleatório", "set_clean_mode", "PT: with mode"),
    ("use spiral mode", "set_clean_mode", "EN: with mode"),
    ("switch to random mode", "set_clean_mode", "EN: switch"),
    ("mop mode", "set_clean_mode", "EN: mop"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(agent, message: str, user_id: str = "eval") -> tuple[str, Optional[str], Optional[dict]]:
    return execute_agent(agent, message, user_id)


# ---------------------------------------------------------------------------
# Parametrized intent tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message,expected_action,description", INTENT_CASES)
def test_intent(agent, message: str, expected_action: str, description: str):
    _, action, _ = _run(agent, message)
    assert action == expected_action, (
        f"[{description}] '{message}'\n"
        f"  expected action: {expected_action}\n"
        f"  got:             {action}"
    )


# ---------------------------------------------------------------------------
# Language detection tests (response language should match input language)
# ---------------------------------------------------------------------------

LANGUAGE_CASES = [
    ("começa a limpar", ["certo", "iniciando", "limpeza", "robô"], "PT response"),
    ("start cleaning", ["got", "starting", "cleaning", "robot"], "EN response"),
]


@pytest.mark.parametrize("message,expected_words,description", LANGUAGE_CASES)
def test_response_language(agent, message: str, expected_words: list, description: str):
    response, _, _ = _run(agent, message)
    lower = response.lower()
    matched = [w for w in expected_words if w in lower]
    assert matched, (
        f"[{description}] Response '{response}' did not contain "
        f"any of the expected words: {expected_words}"
    )


# ---------------------------------------------------------------------------
# Memory / context test
# ---------------------------------------------------------------------------

def test_memory_do_again(agent):
    """Agent should infer 'do that again' from conversation history."""
    uid = "eval_memory_test"
    _run(agent, "start cleaning", user_id=uid)
    response, action, _ = _run(agent, "do that again", user_id=uid)
    assert action == "start_cleaning", (
        f"Expected agent to repeat 'start_cleaning' from memory, got '{action}'. "
        f"Response: '{response}'"
    )


# ---------------------------------------------------------------------------
# Latency benchmark (informational, never fails)
# ---------------------------------------------------------------------------

LATENCY_CASES = [
    "começa a limpar",
    "return to base",
    "modo espiral",
]


@pytest.mark.parametrize("message", LATENCY_CASES)
def test_latency(agent, message: str):
    start = time.perf_counter()
    _run(agent, message, user_id="eval_latency")
    elapsed = time.perf_counter() - start
    print(f"\n  [{message}] → {elapsed:.2f}s")
    # Informational only — no hard limit, output is visible with -v -s
