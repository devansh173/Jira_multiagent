from flask import Blueprint, request, jsonify, session
from app import db
from app.models.conversation import Conversation
from app.agents.input_agent    import process_input
from app.agents.context_agent  import enrich_with_context
from app.agents.jira_agent     import execute_jira_task
from app.agents.response_agent import generate_response
import uuid

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat", methods=["POST"])
def chat():
    data    = request.get_json()
    message = data.get("message", "")

    # Get or create session
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]

    # Load conversation history from DB
    history_rows = Conversation.query.filter_by(session_id=session_id)\
                                     .order_by(Conversation.created_at).all()
    history = [row.to_dict() for row in history_rows]

    # ── Agent Pipeline ──────────────────────────────────
    input_result    = process_input(message)                    # Agent 1
    enriched        = enrich_with_context(history, input_result) # Agent 2
    jira_result     = execute_jira_task(enriched)               # Agent 3
    final_response  = generate_response(jira_result, message)   # Agent 4
    # ────────────────────────────────────────────────────

    # Save to DB
    db.session.add(Conversation(session_id=session_id, role="user",      content=message))
    db.session.add(Conversation(session_id=session_id, role="assistant", content=final_response))
    db.session.commit()

    return jsonify({"response": final_response})


@chat_bp.route("/history", methods=["GET"])
def history():
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"history": []})
    rows = Conversation.query.filter_by(session_id=session_id)\
                             .order_by(Conversation.created_at).all()
    return jsonify({"history": [r.to_dict() for r in rows]})