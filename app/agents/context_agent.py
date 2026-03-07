from app.config import Config
from openai import AzureOpenAI
import json
import re

client = AzureOpenAI(
    azure_endpoint = Config.AZURE_OPENAI_ENDPOINT,
    api_key        = Config.AZURE_OPENAI_API_KEY,
    api_version    = "2024-12-01-preview"
)

SYSTEM_PROMPT = """
You are a context and summarization agent. You receive:
1. The full conversation history
2. A structured request from the input agent

Your job is to:
- Summarize relevant past context
- Enrich the request with any missing details from history
- Return an enriched JSON ready for the Jira agent

You MUST respond with ONLY a valid JSON object. No explanation, no markdown, no backticks.
Example format:
{"intent": "create_ticket", "extracted_details": {}, "context_summary": ""}
"""

def _parse_json_safe(text: str) -> dict:
    """Strip markdown fences and parse JSON safely."""
    # Remove ```json ... ``` or ``` ... ``` wrappers if present
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: return raw text wrapped in a dict
        return {"intent": "unknown", "extracted_details": {}, "raw_response": text}

def enrich_with_context(history: list, input_agent_result: dict) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": f"Input agent result: {json.dumps(input_agent_result)}"}
    ]
    response = client.chat.completions.create(
        model    = Config.AZURE_OPENAI_DEPLOYMENT,
        messages = messages
        # No response_format here — not supported by all models
    )
    return _parse_json_safe(response.choices[0].message.content)