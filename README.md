# Jira Multi-Agent System

> An AI-powered Flask application that lets you manage Jira tickets through natural language conversation, powered by Azure AI Foundry Agents, Azure SQL, and the Jira Cloud REST API.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [The 4-Agent Pipeline](#the-4-agent-pipeline)
- [Azure AI Foundry](#azure-ai-foundry)
- [Azure SQL Database](#azure-sql-database)
- [Jira Cloud Integration](#jira-cloud-integration)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Setup & Installation](#setup--installation)
- [API Reference](#api-reference)
- [How a Request Flows](#how-a-request-flows)

---

## Project Overview

The Jira Multi-Agent System is a Flask web application that enables users to manage Jira tickets through plain English conversation. Instead of navigating the Jira UI, users simply type what they need — the system's AI agents collaborate to understand the request, retrieve context, execute the Jira operation, and respond in a friendly way.

**What it can do:**
- Create Jira tickets with summary, description, priority, and issue type
- Query and list tickets with filters for status, assignee, and keyword
- Update existing tickets — summary, description, priority, assignee
- Transition ticket status through Jira workflow states
- Fetch details of a specific ticket by key
- Maintain full conversation context across a session

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Web Framework | Flask | HTTP routing, session management |
| AI Agents | Azure AI Foundry (`azure-ai-projects==1.0.0b11`) | Real stateful cloud agents |
| Agent Auth | DefaultAzureCredential (`azure-identity`) | Passwordless auth via Azure CLI / Managed Identity |
| LLM Model | `gpt-oss-120b` (configurable) | Powers all AI agents |
| Database | Azure SQL + SQLAlchemy + Flask-Migrate | Conversation history persistence |
| Jira | Jira Cloud REST API v3 | Ticket operations |
| ORM | SQLAlchemy | Database abstraction layer |
| Config | python-dotenv | Environment variable management |

---

## System Architecture

```
User (curl / browser)
        │
        ▼
┌──────────────────┐
│   Flask Route    │  /chat POST
│   chat.py        │  Loads session + conversation history from Azure SQL
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    Agent 1       │  INPUT AGENT
│  input_agent.py  │  Parses intent + extracts structured details
│  [Azure Foundry] │  Returns: {intent, extracted_details, context_needed}
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    Agent 2       │  CONTEXT AGENT
│ context_agent.py │  Enriches with full conversation history
│  [Azure Foundry] │  Returns: {intent, extracted_details, context_summary}
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    Agent 3       │  JIRA AGENT
│  jira_agent.py   │  Routes to correct Jira API call 
│  + JiraMCP       │  Returns: Jira API result JSON
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    Agent 4       │  RESPONSE AGENT
│response_agent.py │  Formats Jira result into friendly message
│  [Azure Foundry] │  Returns: Human-readable response string
└────────┬─────────┘
         │
         ▼
  Save both user message + assistant response to Azure SQL
         │
         ▼
  Return JSON response to user
```

---

## The 4-Agent Pipeline

### Agent 1 — Input Agent (`app/agents/input_agent.py`)

The first agent receives the raw user message and turns it into structured data. It identifies the **intent** (what the user wants to do) and **extracts details** like project key, summary, priority, and ticket ID.

**Input:** Raw user string — e.g. `"create a high priority bug for login page crash"`

**Output:**
```json
{
  "intent": "create_ticket",
  "extracted_details": {
    "project": "SCRUM",
    "summary": "Login page crash",
    "priority": "High",
    "issue_type": "Bug"
  },
  "context_needed": []
}
```

**Supported intents:** `create_ticket`, `update_ticket`, `query_tickets`, `get_ticket`

---

### Agent 2 — Context Agent (`app/agents/context_agent.py`)

The second agent receives Agent 1's structured output along with the **full conversation history** loaded from Azure SQL. Its job is to enrich the request with missing details from past messages and resolve ambiguity.

For example, if the user says `"update that ticket"` without specifying which ticket, Agent 2 looks at the history to find the most recently mentioned ticket key and fills it in.

**Input:** Conversation history (list of `{role, content}` dicts) + Agent 1 JSON output

**Output:**
```json
{
  "intent": "update_ticket",
  "extracted_details": {
    "ticket_id": "SCRUM-3",
    "priority": "Critical"
  },
  "context_summary": "User previously created SCRUM-3 and now wants to update its priority."
}
```

---

### Agent 3 — Jira Agent (`app/agents/jira_agent.py`)

The third agent is the only one that . It is pure deterministic routing — it reads the `intent` from Agent 2's output and calls the correct method on `JiraMCP`.

```python
if intent == "create_ticket":   → jira.create_issue(details)
if intent == "update_ticket":   → jira.update_issue(details)
if intent == "query_tickets":   → jira.search_issues(details)
if intent == "get_ticket":      → jira.get_issue(issue_key)
```

`JiraMCP` (`app/mcp/jira_mcp.py`) handles the actual Jira Cloud REST API calls using HTTP Basic Auth (email + API token).

---

### Agent 4 — Response Agent (`app/agents/response_agent.py`)

The final agent receives both the original user message and the raw Jira API result. It formats everything into a clear, friendly, conversational response that the user actually sees.

**Input:** Original message + Jira result JSON

**Output:** `"I've created ticket SCRUM-4 for the login page crash with High priority. You can view it here: https://yourname.atlassian.net/browse/SCRUM-4 🎉"`

---

## Azure AI Foundry

### What is Azure AI Foundry?

Azure AI Foundry is Microsoft's unified platform for building, deploying, and managing AI applications and agents in the cloud. It provides:

- A **model catalog** with hundreds of models including OpenAI GPT, Meta Llama, Mistral, and other open-source models
- A **managed Agent Service** that handles thread management, run lifecycle, and tool calling
- A **project-based structure** where all resources (models, agents, connections) live under a single project endpoint
- Enterprise-grade security with **DefaultAzureCredential** and Managed Identity support

### How We Use It

Each of the 3 LLM-powered agents (Agents 1, 2, and 4) creates a real Foundry Agent via the `azure-ai-projects` SDK:

```
AIProjectClient
    └── client.agents.create_agent()     → Creates a stateful agent in the cloud
    └── client.agents.threads.create()   → Creates a conversation thread
    └── client.agents.messages.create()  → Posts a message to the thread
    └── client.agents.runs.create_and_process()  → Runs the agent, waits for response
    └── client.agents.messages.list()    → Retrieves the agent's response
    └── client.agents.delete_agent()     → Cleans up after use
    └── client.agents.threads.delete()   → Cleans up the thread
```

### Authentication — DefaultAzureCredential

Instead of API keys, we use `DefaultAzureCredential` from the `azure-identity` package. It automatically tries multiple auth methods in order:

1. **Locally:** Uses your `az login` session (Azure CLI)
2. **On Azure:** Uses Managed Identity automatically — no secrets needed

This means the same code works in both development and production with zero changes and no secrets to manage.

### Model Flexibility

The model is configured in a single place in `app/config.py`:

```python
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-oss-120b")
```

To switch all 4 agents to a different model (e.g. `gpt-4o`, `Llama-3.3-70B`, `Mistral-large`), change this one variable in your `.env` file. No other code changes required.

### Project Endpoint

The Foundry project endpoint format is:
```
https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
```

This is different from the standard Azure OpenAI endpoint and is required for the Agent Service.

---

## Azure SQL Database

### What We Store

The `conversations` table stores every message exchanged in every session:

| Column | Type | Purpose |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `session_id` | String(100) | Links messages to a user session (UUID from Flask cookie) |
| `role` | String(20) | Either `"user"` or `"assistant"` |
| `content` | Text | The full message content |
| `created_at` | DateTime | Timestamp, used for ordering history |

### Why Azure SQL

- Fully managed — no server maintenance
- Serverless tier available for dev/low traffic (scales to zero)
- Native SQLAlchemy support via `pyodbc` and ODBC Driver 18
- Connection pooling handles the aggressive idle timeout Azure SQL enforces

### Connection Pool Configuration

Azure SQL closes idle connections aggressively. We configure SQLAlchemy to handle this gracefully:

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,   # Test connection before use, get fresh if closed
    "pool_recycle":  1800,   # Recycle connections every 30 minutes
    "pool_size":     5,      # Keep 5 permanent connections ready
    "max_overflow":  10,     # Allow 10 extra connections under high load
}
```

`pool_pre_ping` is the critical setting — it prevents the `TCP Provider: connection forcibly closed` error that Azure SQL causes on idle connections.

### ORM — SQLAlchemy + Flask-Migrate

SQLAlchemy is used as the ORM (Object Relational Mapper). This means we interact with the database using Python classes instead of raw SQL:

```python
# Save a message
db.session.add(Conversation(session_id=sid, role="user", content=message))
db.session.commit()

# Load history
history = Conversation.query.filter_by(session_id=sid).order_by(Conversation.created_at).all()
```

Flask-Migrate handles database schema changes via Alembic migrations, so you can evolve the schema without losing data.

---

## Jira Cloud Integration

### Authentication

Jira Cloud uses HTTP Basic Auth where:
- **Username:** Your Atlassian account email
- **Password:** An API token (generated at id.atlassian.com/manage-profile/security/api-tokens)

Your real password is never used. API tokens can be revoked independently.

### API Version

We use **Jira REST API v3**. Key endpoints:

| Operation | Method | Endpoint |
|---|---|---|
| Create issue | POST | `/rest/api/3/issue` |
| Update issue | PUT | `/rest/api/3/issue/{key}` |
| Get issue | GET | `/rest/api/3/issue/{key}` |
| Search issues | GET | `/rest/api/3/search/jql` |
| Get transitions | GET | `/rest/api/3/issue/{key}/transitions` |
| Transition issue | POST | `/rest/api/3/issue/{key}/transitions` |

### Atlassian Document Format (ADF)

Jira API v3 requires description fields in **Atlassian Document Format** — a nested JSON structure, not plain text:

```json
{
  "type": "doc",
  "version": 1,
  "content": [{
    "type": "paragraph",
    "content": [{ "type": "text", "text": "Your description here" }]
  }]
}
```

### JQL — Jira Query Language

When searching tickets, we build JQL (Jira Query Language) queries dynamically:

```
project = SCRUM AND status = "In Progress" ORDER BY created DESC
```

---

## Project Structure

```
jira-multiagent/
│
├── app/
│   ├── __init__.py              # Flask app factory, db + migrate init
│   ├── config.py                # All config in one place (model name here)
│   │
│   ├── agents/
│   │   ├── input_agent.py       # Agent 1: parse intent + extract details
│   │   ├── context_agent.py     # Agent 2: enrich with conversation history
│   │   ├── jira_agent.py        # Agent 3: route to Jira API 
│   │   └── response_agent.py    # Agent 4: format friendly response
│   │
│   ├── models/
│   │   └── conversation.py      # SQLAlchemy model for conversation history
│   │
│   ├── mcp/
│   │   └── jira_mcp.py          # Jira Cloud REST API client
│   │
│   ├── routes/
│   │   └── chat.py              # Flask routes: /chat and /history
│   │
│   └── utils/
│       ├── ai_client.py         # Azure AI Foundry client factory
│       └── agent_manager.py     # Foundry agent create/run/cleanup utilities
│
├── migrations/                  # Flask-Migrate / Alembic migration files
├── .env                         # Secrets (never commit to Git)
├── requirements.txt             # Python dependencies
└── run.py                       # Flask entry point
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# ── Azure OpenAI / AI Foundry ──────────────────────────────
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-oss-120b        # Change this to swap models

# ── Azure AI Foundry Project ───────────────────────────────
AZURE_FOUNDRY_PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project

# ── Azure SQL Database ─────────────────────────────────────
DATABASE_URL=mssql+pyodbc://username:password@yourserver.database.windows.net/dbname?driver=ODBC+Driver+18+for+SQL+Server

# ── Flask ──────────────────────────────────────────────────
FLASK_SECRET_KEY=change-this-to-a-long-random-string
FLASK_DEBUG=True

# ── Jira Cloud ─────────────────────────────────────────────
JIRA_BASE_URL=https://yourname.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=SCRUM
```



---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Azure account with AI Foundry project created
- Azure SQL Database created
- Jira Cloud account with API token
- ODBC Driver 18 for SQL Server ([download](https://aka.ms/odbc18))
- Azure CLI installed and logged in (`az login`)

### Steps

```bash
# 1. Clone and create virtual environment
git clone <your-repo>
cd jira-multiagent
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install flask flask-sqlalchemy flask-migrate openai python-dotenv
pip install pyodbc sqlalchemy requests jira azure-identity
pip install azure-ai-projects==1.0.0b11 azure-ai-inference

# 3. Configure environment
# Copy .env template above and fill in your values

# 4. Login to Azure (required for DefaultAzureCredential)
az login

# 5. Initialize database
flask --app run db init
flask --app run db migrate -m "initial"
flask --app run db upgrade

# 6. Run the application
python run.py
```

---

## API Reference

### POST `/chat`

Send a message to the agent pipeline.

**Request:**
```json
{ "message": "create a high priority bug for login page crash" }
```

**Response:**
```json
{
  "response": "I've created ticket SCRUM-4 'Login page crash' with High priority. View it at https://yourname.atlassian.net/browse/SCRUM-4 🎉"
}
```

### GET `/history`

Retrieve the conversation history for the current session.

**Response:**
```json
{
  "history": [
    { "role": "user", "content": "create a high priority bug for login page crash" },
    { "role": "assistant", "content": "I've created ticket SCRUM-4..." }
  ]
}
```

---

## How a Request Flows

Here is a complete walkthrough of what happens when a user sends `"create a high priority bug for login page crash"`:

**1. Flask receives the POST request** at `/chat`, reads the session cookie to get `session_id`, and loads all past messages for this session from Azure SQL.

**2. Agent 1 (Input Agent)** creates a real Foundry Agent in Azure, creates a thread, posts the user message, runs the agent, and gets back structured JSON identifying intent as `create_ticket` with details like summary and priority. The agent and thread are deleted after.

**3. Agent 2 (Context Agent)** creates another Foundry Agent, posts the conversation history along with Agent 1's output, and gets back an enriched JSON that fills in any missing details from past messages. Cleaned up after.

**4. Agent 3 (Jira Agent)** reads `intent = "create_ticket"` and calls `jira.create_issue(details)` which sends a POST request to the Jira Cloud REST API. Jira creates the ticket and returns the new ticket key and URL.

**5. Agent 4 (Response Agent)** creates a final Foundry Agent, receives both the original message and the Jira result, and generates a friendly human-readable response. Cleaned up after.

**6. Flask saves** both the user message and the assistant response to Azure SQL, then returns the final response as JSON.

---

## Switching Models

To use a different model for all agents, change a single line in `.env`:

```env
# Use GPT-4o
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Use Llama 3.3
AZURE_OPENAI_DEPLOYMENT=Llama-3.3-70B-Instruct

# Use Mistral Large
AZURE_OPENAI_DEPLOYMENT=Mistral-large-2411
```

The model must be deployed in your Azure AI Foundry project. No code changes required.

---

*Built with Flask · Azure AI Foundry · Azure SQL · Jira Cloud REST API v3*