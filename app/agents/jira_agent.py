from app.mcp.jira_mcp import JiraMCP

jira = JiraMCP()

def execute_jira_task(enriched_request: dict) -> dict:
    intent  = enriched_request.get("intent", "")
    details = enriched_request.get("extracted_details", {})

    if intent == "create_ticket":
        return jira.create_issue(details)
    elif intent == "update_ticket":
        return jira.update_issue(details)
    elif intent == "query_tickets":
        return jira.search_issues(details)
    elif intent == "get_ticket":
        issue_key = details.get("ticket_id") or details.get("issue_key")
        return jira.get_issue(issue_key)
    else:
        return {"status": "error", "detail": f"Unknown intent: {intent}"}