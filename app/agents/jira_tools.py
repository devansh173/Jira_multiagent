import json
from app.mcp.jira_mcp import JiraMCP

jira = JiraMCP()

def create_jira_ticket(project: str, summary: str, description: str, priority: str, issue_type: str) -> str:
    """
    Creates a new Jira ticket in the specified project.

    :param project: The Jira project key e.g. SCRUM or TEST
    :param summary: Short title/summary of the ticket
    :param description: Detailed description of the issue
    :param priority: Priority level - one of: Lowest, Low, Medium, High, Highest
    :param issue_type: Type of issue - one of: Bug, Task, Story, Epic
    :return: JSON string with ticket key, ID and URL if successful, or error details
    """
    details = {
        "project":     project,
        "summary":     summary,
        "description": description,
        "priority":    priority,
        "issue_type":  issue_type
    }
    result = jira.create_issue(details)
    return json.dumps(result)


def update_jira_ticket(ticket_id: str, summary: str = "", description: str = "", priority: str = "", status: str = "") -> str:
    """
    Updates an existing Jira ticket by its key.

    :param ticket_id: The Jira ticket key e.g. SCRUM-3
    :param summary: New summary/title for the ticket (optional)
    :param description: New description for the ticket (optional)
    :param priority: New priority - one of: Lowest, Low, Medium, High, Highest (optional)
    :param status: New status to transition to e.g. In Progress, Done, To Do (optional)
    :return: JSON string with updated ticket details or error
    """
    details = {"ticket_id": ticket_id}
    if summary:     details["summary"]     = summary
    if description: details["description"] = description
    if priority:    details["priority"]    = priority
    if status:      details["status"]      = status
    result = jira.update_issue(details)
    return json.dumps(result)


def search_jira_tickets(project: str, status: str = "", assignee: str = "", keyword: str = "") -> str:
    """
    Searches and lists Jira tickets in a project with optional filters.

    :param project: The Jira project key to search in e.g. SCRUM
    :param status: Filter by status e.g. To Do, In Progress, Done (optional)
    :param assignee: Filter by assignee name or email (optional)
    :param keyword: Filter by keyword in ticket summary (optional)
    :return: JSON string with list of matching tickets or error
    """
    details = {
        "project":  project,
        "status":   status,
        "assignee": assignee,
        "keyword":  keyword
    }
    result = jira.search_issues(details)
    return json.dumps(result)


def get_jira_ticket(ticket_id: str) -> str:
    """
    Retrieves full details of a specific Jira ticket by its key.

    :param ticket_id: The Jira ticket key e.g. SCRUM-3
    :return: JSON string with ticket details including summary, status, priority and URL
    """
    result = jira.get_issue(ticket_id)
    return json.dumps(result)


# This set is what we pass to FunctionTool
# Foundry reads each function's docstring to build the tool schema automatically
jira_functions = {
    create_jira_ticket,
    update_jira_ticket,
    search_jira_tickets,
    get_jira_ticket
}