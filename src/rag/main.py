"""
Simple example showing how to do a local RAG (retrieve-and-generate) flow
against an OpenAI API-enabled vLLM model that does NOT support tool calling.

Usage:
  - Set OPENAI_API_KEY in your environment (and OPENAI_API_BASE if required by your deployment).
    Example:
      export OPENAI_API_KEY="sk-..."
      # if using a custom OpenAI-compatible endpoint:
      export OPENAI_API_BASE="https://your-openai-compatible-endpoint.example.com"

  - Run:
      python3 scripts/vllm_rag_example.py
"""

import os
from typing import List, Dict, Any, cast
from openai import OpenAI

# Replace with the exact model name your vLLM exposes via the OpenAI-compatible API.
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "swiss-ai/Apertus-8B-Instruct-2509")

# A tiny mock knowledge base for this example. In a real RAG pipeline you'd use
# a vector DB (e.g., FAISS, Pinecone) and dense retrieval.
MOCK_KB = [
    {"id": "doc1", "source": "KB:Intro", "text": "vLLM is a high-performance LLM runtime optimized for inference."},
    {"id": "doc2", "source": "KB:Setup", "text": "To configure vLLM behind an OpenAI-compatible API, set the API endpoint and model mapping."},
    {"id": "doc3", "source": "KB:Limitations", "text": "This particular vLLM does not support tool-calling or external function invocation."},
    {"id": "doc4", "source": "KB:Usage", "text": "When doing RAG, retrieve relevant passages and include them in the prompt for the model to use."},
]


def retrieve_documents(query: str, k: int = 3) -> List[Dict]:
    """
    Mock retriever: ranks KB entries by simple keyword overlap with the query.
    Returns top-k documents (as dicts with id/source/text).
    """
    q_tokens = set([t.strip().lower() for t in query.split() if t.strip()])
    scored = []
    for doc in MOCK_KB:
        doc_tokens = set(doc["text"].lower().split())
        # simple overlap score
        score = len(q_tokens & doc_tokens)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_docs = [doc for score, doc in scored if score > 0][:k]
    # If nothing matched, fall back to the top k by default order
    if not top_docs:
        top_docs = MOCK_KB[:k]
    return top_docs


def build_rag_messages(query: str, retrieved: List[Dict]) -> List[Dict]:
    """
    Build the chat messages for the model including the retrieved context.
    We explicitly add a system message instructing the model to only use the
    provided context and to acknowledge when the answer is not in the docs.
    """
    context_chunks = []
    for i, doc in enumerate(retrieved, start=1):
        context_chunks.append(f"[{i}] Source: {doc['source']}\n{doc['text']}")
    context_text = "\n\n".join(context_chunks)

    system_msg = (
        "You are a helpful assistant. Use ONLY the provided context to answer the user's question. "
        "If the answer is not present in the provided context, say you don't know rather than hallucinating."
    )

    user_msg = (
        f"Context (retrieved documents):\n{context_text}\n\n"
        f"User question: {query}\n\n"
        "Answer concisely and cite sources (e.g., [1], [2]) if applicable."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def build_user_rag_content(query: str, retrieved: List[Dict]) -> str:
    """
    Build only the user content that includes retrieved context for a RAG-style prompt.
    This keeps the system message stable across the conversation while allowing
    retrieval to be plugged in per user turn.
    """
    context_chunks = []
    for i, doc in enumerate(retrieved, start=1):
        context_chunks.append(f"[{i}] Source: {doc['source']}\n{doc['text']}")
    context_text = "\n\n".join(context_chunks) if context_chunks else "(no retrieved context)"

    return (
        f"Context (retrieved documents):\n{context_text}\n\n"
        f"User question: {query}\n\n"
        "Answer concisely and cite sources (e.g., [1], [2]) if applicable."
    )


def print_help() -> None:
    print(
        "Commands:\n"
        "  /help     Show this help message\n"
        "  /history  Show the conversation history (user + assistant turns)\n"
        "  /clear    Clear the conversation history (keeps system message)\n"
        "  /exit     Exit the chat\n"
    )


def show_history(history: List[Dict]) -> None:
    if not history:
        print("(no history yet)")
        return
    print("--- Conversation history ---")
    for i, m in enumerate(history, start=1):
        role = m.get("role", "unknown")
        content = m.get("content", "")
        # Print only first line for brevity with an index
        first_line = content.splitlines()[0] if content else ""
        print(f"{i}. {role}: {first_line}")
    print("----------------------------")


def query_vllm_model(messages: List[Dict], model: str = VLLM_MODEL_NAME) -> str | None:
    """
    Call the OpenAI-compatible API to get a completion from the vLLM model.
    This assumes the OpenAI Python SDK is configured via environment variables.
    """
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="dummy"
    )  
    # The OpenAI SDK typings expect specific message parameter types; cast to Any
    # to satisfy static type checkers while keeping runtime behavior unchanged.
    resp = client.chat.completions.create(
        model=model,
        messages=cast(Any, messages),
        temperature=0.0,
        max_tokens=512,
    )

    # The SDK returns choices; we take the first message content.
    # Depending on SDK version, the exact attribute access may vary.
    try:
        return resp.choices[0].message.content
    except Exception:
        # Fallback for possible different response shapes
        return str(resp)


def main():
    # Stable system instruction for the entire chat session
    system_msg = {
        "role": "system",
        "content": (
            "You are a helpful assistant. Use ONLY the provided context to answer the user's question. "
            "If the answer is not present in the provided context, say you don't know rather than hallucinating."
        ),
    }

    # In-memory chat history of user and assistant messages. The system message is
    # kept separate and prefixed to the messages sent to the model each turn.
    history: List[Dict] = []

    print("Starting multi-turn RAG chat with vLLM. Type /help for commands.")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        if user_input.lower() in ("/exit", "exit", "quit"):
            print("Exiting chat. Goodbye!")
            break
        if user_input.lower() == "/help":
            print_help()
            continue
        if user_input.lower() == "/history":
            show_history(history)
            continue
        if user_input.lower() == "/clear":
            history.clear()
            print("Conversation history cleared.")
            continue

        # Normal user query -> perform retrieval and send the full conversation
        # (system + history + new user message-with-context) to the model.
        retrieved_docs = retrieve_documents(user_input, k=3)
        #print(f"\nRetrieved {len(retrieved_docs)} document(s):")
        for i, d in enumerate(retrieved_docs, start=1):
            #print(f"  [{i}] {d['id']} ({d['source']})")

        user_message = {"role": "user", "content": build_user_rag_content(user_input, retrieved_docs)}

        # Append the new user message to history so that subsequent turns remember it
        history.append(user_message)

        # Build the full messages to send to the model: system + history
        messages = [system_msg] + history
        print("\nSending prompt to vLLM model...\n")

        assistant_reply = query_vllm_model(messages)
        if assistant_reply is None:
            assistant_reply = "(no response from model)"

        # Append assistant reply to history and display it to the user
        history.append({"role": "assistant", "content": assistant_reply})

        print("\nAssistant:")
        print(assistant_reply)
        print()


if __name__ == "__main__":
    main()