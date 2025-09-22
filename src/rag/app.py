"""
Chainlit app that mirrors the console RAG flow in main.py.

This app re-uses the mocked retrieval and vLLM call defined in `main.py`
and exposes a multi-turn chat UI via Chainlit. It supports simple commands:
  - /help: show available commands
  - /history: display the conversation history
  - /clear: clear the conversation history

How it works per turn:
  - retrieve relevant docs from the mocked KB
  - build a user message that includes retrieved context
  - send system + conversation history to the vLLM-compatible OpenAI API
  - stream the assistant response back to the Chainlit UI

Note: This file imports helper functions from `main.py` (same folder).
"""

from typing import List, Dict
import chainlit as cl

# Import the retriever, prompt builder and model caller from main.py to avoid
# duplicating logic. main.py safely defines functions without running the
# interactive CLI when imported.
import main as rag_main


HELP_TEXT = (
    "Commands:\n"
    "  /help     Show this help message\n"
    "  /history  Show the conversation history (user + assistant turns)\n"
    "  /clear    Clear the conversation history (keeps system message)\n"
)




@cl.on_chat_start
async def on_chat_start():
    """Initialize session state: a stable system message and an empty history."""
    system_msg = {
        "role": "system",
        "content": (
            "You are a helpful assistant. Use ONLY the provided context to answer the user's question. "
            "If the answer is not present in the provided context, say you don't know rather than hallucinating."
        ),
    }
    cl.user_session.set("system_msg", system_msg)
    cl.user_session.set("history", [])


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()
    if not text:
        return

    # Handle local commands
    if text.lower() == "/help":
        help_msg = cl.Message(content=HELP_TEXT)
        await help_msg.send()
        return

    if text.lower() == "/history":
        history: List[Dict] = cl.user_session.get("history") or []
        if not history:
            await cl.Message(content="(no history yet)").send()
            return
        formatted = [f"{i+1}. {m['role']}: {m['content'].splitlines()[0]}" for i, m in enumerate(history)]
        await cl.Message(content="\n".join(formatted)).send()
        return

    if text.lower() == "/clear":
        cl.user_session.set("history", [])
        await cl.Message(content="Conversation history cleared.").send()
        return

    # Normal user message -> run retrieval (mocked) and call the model
    retrieved_docs = rag_main.retrieve_documents(text, k=3)
    # Show retrieved docs in the UI for transparency
    if retrieved_docs:
        retrieved_summary = "\n".join([f"[{i+1}] {d['id']} ({d['source']})" for i, d in enumerate(retrieved_docs)])
        await cl.Message(content=f"Retrieved {len(retrieved_docs)} documents:\n{retrieved_summary}").send()

    # Build the user message that includes retrieved context
    user_msg_content = rag_main.build_user_rag_content(text, retrieved_docs)
    user_message = {"role": "user", "content": user_msg_content}

    # Append user message to history and persist
    history: List[Dict] = cl.user_session.get("history") or []
    history.append(user_message)
    cl.user_session.set("history", history)

    # Prepare the conversation for the model: system + history
    system_msg = cl.user_session.get("system_msg")
    messages = [system_msg] + history

    # Query the vLLM model via the OpenAI-compatible helper
    assistant_reply = rag_main.query_vllm_model(messages)
    if assistant_reply is None:
        assistant_reply = "(no response from model)"

    # Stream the assistant reply back to Chainlit and record it in history
    answer = cl.Message(content="")
    await answer.stream_token(assistant_reply)

    history.append({"role": "assistant", "content": assistant_reply})
    cl.user_session.set("history", history)
