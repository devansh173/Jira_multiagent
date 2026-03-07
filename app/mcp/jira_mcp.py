import requests
from requests.auth import HTTPBasicAuth
from app.config import Config
import json

class JiraMCP:
    def __init__(self):
        self.base_url = Config.JIRA_BASE_URL
        self.auth     = HTTPBasicAuth(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        self.headers  = {
            "Accept":       "application/json",
            "Content-Type": "application/json"
        }
        self.project_key = Config.JIRA_PROJECT_KEY

    # ─── Create Issue ─────────────────────────────────────
    def create_issue(self, details: dict) -> dict:
        url     = f"{self.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project":     {"key": details.get("project", self.project_key)},
                "summary":     details.get("summary", "New Issue"),
                "description": {
                    "type":    "doc",
                    "version": 1,
                    "content": [{
                        "type":    "paragraph",
                        "content": [{
                            "type": "text",
                            "text": details.get("description", "")
                        }]
                    }]
                },
                "issuetype": {"name": details.get("issue_type", "Task")},
                "priority":  {"name": details.get("priority", "Medium")}
            }
        }

        # Add assignee if provided
        if details.get("assignee"):
            payload["fields"]["assignee"] = {"accountId": details["assignee"]}

        response = requests.post(
            url,
            headers = self.headers,
            auth    = self.auth,
            data    = json.dumps(payload)
        )

        if response.status_code == 201:
            data = response.json()
            return {
                "status":   "success",
                "action":   "create_issue",
                "issue_id": data["id"],
                "issue_key": data["key"],
                "url":      f"{self.base_url}/browse/{data['key']}"
            }
        else:
            return {
                "status": "error",
                "action": "create_issue",
                "code":   response.status_code,
                "detail": response.text
            }

    # ─── Update Issue ─────────────────────────────────────
    def update_issue(self, details: dict) -> dict:
        issue_key = details.get("ticket_id") or details.get("issue_key")
        if not issue_key:
            return {"status": "error", "detail": "No ticket ID provided"}

        url    = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        fields = {}

        if details.get("summary"):
            fields["summary"] = details["summary"]
        if details.get("priority"):
            fields["priority"] = {"name": details["priority"]}
        if details.get("status"):
            # Status changes need a transition call (handled separately)
            return self._transition_issue(issue_key, details["status"])
        if details.get("description"):
            fields["description"] = {
                "type":    "doc",
                "version": 1,
                "content": [{
                    "type":    "paragraph",
                    "content": [{"type": "text", "text": details["description"]}]
                }]
            }

        response = requests.put(
            url,
            headers = self.headers,
            auth    = self.auth,
            data    = json.dumps({"fields": fields})
        )

        if response.status_code == 204:
            return {
                "status":    "success",
                "action":    "update_issue",
                "issue_key": issue_key,
                "url":       f"{self.base_url}/browse/{issue_key}"
            }
        else:
            return {
                "status": "error",
                "action": "update_issue",
                "code":   response.status_code,
                "detail": response.text
            }

    # ─── Transition Issue Status ──────────────────────────
    def _transition_issue(self, issue_key: str, target_status: str) -> dict:
        # Get available transitions
        url       = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        response  = requests.get(url, headers=self.headers, auth=self.auth)
        transitions = response.json().get("transitions", [])

        # Find matching transition
        match = next(
            (t for t in transitions if target_status.lower() in t["name"].lower()),
            None
        )
        if not match:
            return {"status": "error", "detail": f"No transition found for status: {target_status}"}

        # Execute transition
        response = requests.post(
            url,
            headers = self.headers,
            auth    = self.auth,
            data    = json.dumps({"transition": {"id": match["id"]}})
        )
        return {
            "status":    "success" if response.status_code == 204 else "error",
            "action":    "transition_issue",
            "issue_key": issue_key,
            "new_status": target_status
        }

    # ─── Search Issues ────────────────────────────────────
    def search_issues(self, details: dict) -> dict:
        project  = details.get("project", self.project_key)
        status   = details.get("status", "")
        assignee = details.get("assignee", "")
        keyword  = details.get("keyword", "")

        # Build JQL query
        jql_parts = [f"project = {project}"]
        if status:
            jql_parts.append(f'status = "{status}"')
        if assignee:
            jql_parts.append(f'assignee = "{assignee}"')
        if keyword:
            jql_parts.append(f'summary ~ "{keyword}"')

        jql = " AND ".join(jql_parts) + " ORDER BY created DESC"

        url      = f"{self.base_url}/rest/api/3/search"
        response = requests.get(
            url,
            headers = self.headers,
            auth    = self.auth,
            params  = {"jql": jql, "maxResults": 10, "fields": "summary,status,priority,assignee"}
        )

        if response.status_code == 200:
            data   = response.json()
            issues = [{
                "key":      i["key"],
                "summary":  i["fields"]["summary"],
                "status":   i["fields"]["status"]["name"],
                "priority": i["fields"]["priority"]["name"] if i["fields"].get("priority") else "None",
                "url":      f"{self.base_url}/browse/{i['key']}"
            } for i in data.get("issues", [])]
            return {
                "status": "success",
                "action": "search_issues",
                "total":  data["total"],
                "issues": issues
            }
        else:
            return {
                "status": "error",
                "action": "search_issues",
                "code":   response.status_code,
                "detail": response.text
            }

    # ─── Get Single Issue ─────────────────────────────────
    def get_issue(self, issue_key: str) -> dict:
        url      = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        response = requests.get(url, headers=self.headers, auth=self.auth)

        if response.status_code == 200:
            data = response.json()
            return {
                "status":      "success",
                "action":      "get_issue",
                "issue_key":   issue_key,
                "summary":     data["fields"]["summary"],
                "description": data["fields"].get("description", ""),
                "status":      data["fields"]["status"]["name"],
                "priority":    data["fields"]["priority"]["name"],
                "url":         f"{self.base_url}/browse/{issue_key}"
            }
        else:
            return {"status": "error", "code": response.status_code, "detail": response.text}