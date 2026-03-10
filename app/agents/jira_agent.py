from azure.ai.agents.models import FunctionTool, ToolSet, MessageRole
from app.utils.ai_client import get_project_client
from app.utils.agent_manager import create_thread, cleanup
from app.agents.jira_tools import jira_functions
from app.config import Config
import json

INSTRUCTIONS = """
You are a Jira operations agent. You have access to tools to:
- Create Jira tickets
- Update existing Jira tickets
- Search and list tickets in a project
- Get details of a specific ticket

Based on the enriched request you receive, call the appropriate tool with the correct parameters.
Always use the project key from the request. Return the raw tool result.
"""

def execute_jira_task(enriched_request: dict) -> dict:
    client    = get_project_client()
    thread_id = create_thread(client)

   
    functions = FunctionTool(functions=jira_functions)
    toolset   = ToolSet()
    toolset.add(functions)

    
    client.agents.enable_auto_function_calls(toolset)

    
    agent = client.agents.create_agent(
        model        = Config.AZURE_OPENAI_DEPLOYMENT,
        name         = "jira-agent",
        instructions = INSTRUCTIONS,
        toolset      = toolset
    )

    try:
        
        client.agents.messages.create(
            thread_id = thread_id,
            role      = MessageRole.USER,
            content   = f"Execute this Jira request: {json.dumps(enriched_request)}"
        )

        
        run = client.agents.runs.create_and_process(
            thread_id = thread_id,
            agent_id  = agent.id
        )

        if run.status == "failed":
            return {"status": "error", "detail": f"Agent run failed: {run.last_error}"}

        
        messages = client.agents.messages.list(thread_id=thread_id)
        for msg in messages:
            if msg.role == MessageRole.AGENT:
                for block in msg.content:
                    if hasattr(block, "text"):
                        # Try to parse as JSON, otherwise wrap in dict
                        try:
                            return json.loads(block.text.value)
                        except json.JSONDecodeError:
                            return {"status": "success", "response": block.text.value}

        return {"status": "error", "detail": "No response from Jira agent"}

    finally:
        cleanup(client, agent.id, thread_id)