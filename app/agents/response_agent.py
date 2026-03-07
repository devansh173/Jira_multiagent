from app.config import Config
from openai import AzureOpenAI
import json

client = AzureOpenAI(
    azure_endpoint = Config.AZURE_OPENAI_ENDPOINT,
    api_key        = Config.AZURE_OPENAI_API_KEY,
    api_version    = "2024-12-01-preview"
)

SYSTEM_PROMPT = """
You are a friendly response agent. You receive the result of a Jira operation.
Your job is to explain what happened in a clear, friendly, conversational way to the user.
Be concise, helpful, and positive. If there was an error, explain it simply.
"""

def generate_response(jira_result: dict, original_message: str) -> str:
    response = client.chat.completions.create(
        model    = Config.AZURE_OPENAI_DEPLOYMENT,
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"User asked: {original_message}\nJira result: {json.dumps(jira_result)}"}
        ]
    )
    return response.choices[0].message.content