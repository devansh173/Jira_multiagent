from app.utils.ai_client import get_project_client
from app.utils.agent_manager import create_agent, create_thread, run_agent, cleanup
import json, re

INSTRUCTIONS = """
You are a context and summarization agent. You receive:
1. The full conversation history as JSON
2. A structured request from the input agent

Your job is to:
- Summarize relevant past context
- Enrich the request with any missing details from history
- Return an enriched JSON ready for the Jira agent

You MUST respond with ONLY a valid JSON object. No explanation, no markdown, no backticks.
Example:
{"intent": "create_ticket", "extracted_details": {}, "context_summary": ""}
"""

def _parse_json_safe(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"intent": "unknown", "extracted_details": {}, "raw_response": text}

def enrich_with_context(history: list, input_agent_result: dict) -> dict:
    client    = get_project_client()
    agent     = create_agent(client, "context-agent", INSTRUCTIONS)
    thread_id = create_thread(client)

    message = (
        f"Conversation history: {json.dumps(history)}\n"
        f"Input agent result: {json.dumps(input_agent_result)}"
    )

    try:
        response = run_agent(client, agent.id, thread_id, message)
        return _parse_json_safe(response)
    finally:
        cleanup(client, agent.id, thread_id)