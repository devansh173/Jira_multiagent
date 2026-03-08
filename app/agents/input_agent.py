from app.utils.ai_client import get_project_client
from app.utils.agent_manager import create_agent, create_thread, run_agent, cleanup
from app.config import Config
import json, re

INSTRUCTIONS = f"""
You are an input processing agent. Your job is to:
1. Take the user's raw message
2. Identify the intent (create_ticket, update_ticket, query_tickets, get_ticket)
3. Extract key details (project, summary, description, priority, assignee, ticket_id)
4. Return a clean structured JSON with: intent, extracted_details, context_needed

Default project key is: {Config.JIRA_PROJECT_KEY}
Always include the project key in extracted_details.

You MUST respond with ONLY a valid JSON object. No explanation, no markdown, no backticks.
Example:
{{"intent": "create_ticket", "extracted_details": {{"project": "{Config.JIRA_PROJECT_KEY}", "summary": "...", "priority": "High"}}, "context_needed": []}}
"""

def _parse_json_safe(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {{"intent": "unknown", "extracted_details": {}, "raw_response": text}}

def process_input(user_message: str) -> dict:
    client    = get_project_client()
    agent     = create_agent(client, "input-agent", INSTRUCTIONS)
    thread_id = create_thread(client)

    try:
        response = run_agent(client, agent.id, thread_id, user_message)
        return _parse_json_safe(response)
    finally:
        cleanup(client, agent.id, thread_id)