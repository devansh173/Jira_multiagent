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
You are an input processing agent. Your job is to:
1. Take the user's raw message
2. Identify the intent (create_ticket, update_ticket, query_tickets, delete_ticket)
3. Extract key details (project, summary, description, priority, assignee, ticket_id etc.)
4. Return a clean structured JSON with: intent, extracted_details, context_needed

You MUST respond with ONLY a valid JSON object. No explanation, no markdown, no backticks.
Example format:
{"intent": "create_ticket", "extracted_details": {"summary": "...", "priority": "high"}, "context_needed": []}
"""

def _parse_json_safe(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"intent": "unknown", "extracted_details": {}, "raw_response": text}

def process_input(user_message: str) -> dict:
    response = client.chat.completions.create(
        model    = Config.AZURE_OPENAI_DEPLOYMENT,
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ]
        # No response_format — using prompt enforcement instead
    )
    return _parse_json_safe(response.choices[0].message.content)