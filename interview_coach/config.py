"""Configuration and LLM client setup."""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env from current directory and parent directories
load_dotenv()

# Also try to load from parent directory if key not found
if not os.environ.get("OPENROUTER_API_KEY"):
    # Try parent directories
    import pathlib
    current = pathlib.Path(__file__).parent
    for parent in [current.parent, current.parent.parent]:
        env_file = parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break

# Get API key
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

if not OPENROUTER_API_KEY:
    import warnings
    warnings.warn(
        "OPENROUTER_API_KEY not found! "
        "Create a .env file with OPENROUTER_API_KEY=sk-or-v1-your-key "
        "or set the environment variable."
    )

# OpenRouter API client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# # Model configuration (legacy - single-call Observer)
# OBSERVER_MODEL = "openai/gpt-5.2"
# INTERVIEWER_MODEL = "openai/gpt-5-mini"
# HIRING_MANAGER_MODEL = "openai/gpt-5.2"

# # Hybrid Observer Pipeline models
# CLASSIFIER_MODEL = "openai/gpt-5-mini"      # Fast/cheap for classification
# HALLUCINATION_MODEL = "openai/gpt-5-mini"   # Fast/cheap for fact-check
# GRADER_PLANNER_MODEL = "openai/gpt-5.2"     # Smart model for scoring + planning

# Model configuration (legacy - single-call Observer)
OBSERVER_MODEL = "openai/gpt-5.2"
INTERVIEWER_MODEL = "openai/gpt-5.2"
HIRING_MANAGER_MODEL = "openai/gpt-5.2"

# Hybrid Observer Pipeline models
CLASSIFIER_MODEL = "openai/gpt-5.2"      # Fast/cheap for classification
HALLUCINATION_MODEL = "openai/gpt-5.2"   # Fast/cheap for fact-check
GRADER_PLANNER_MODEL = "openai/gpt-5.2"     # Smart model for scoring + planning

# Interview settings
DEFAULT_DIFFICULTY = 2  # 1-5 scale
MAX_TURNS = 20
MIN_QUESTIONS_FOR_ASSESSMENT = 3


def llm_chat(
    system: str,
    user: str,
    model: str = OBSERVER_MODEL,
    json_mode: bool = False,
) -> str:
    """Send a chat completion request to the LLM.
    
    Args:
        system: System prompt
        user: User message
        model: Model to use
        json_mode: If True, request JSON output
    
    Returns:
        The assistant's response content
    """
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content.strip()


def llm_chat_with_history(
    system: str,
    messages: list[dict],
    model: str = OBSERVER_MODEL,
    json_mode: bool = False,
) -> str:
    """Send a chat completion request with conversation history.
    
    Args:
        system: System prompt
        messages: List of message dicts with 'role' and 'content'
        model: Model to use
        json_mode: If True, request JSON output
    
    Returns:
        The assistant's response content
    """
    full_messages = [{"role": "system", "content": system}] + messages
    
    kwargs = {
        "model": model,
        "messages": full_messages,
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content.strip()
