import os
import chromadb
from sentence_transformers import SentenceTransformer
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from prompt_template import PROMPT_TEMPLATE

MOCK_LLM = os.environ.get("MOCK_LLM", "1") == "1"

POLICY_KEYWORDS = [
    "delivery", "return", "refund", "membership",
    "tracking", "cancel", "gift card", "support hours"
]

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("zepto_policies")


class GraphState(TypedDict):
    query: str
    intent: str
    answer: str
    sources: List[str]
    confidence: float


def classify_intent(state: GraphState) -> GraphState:
    query_lower = state["query"].lower()

    if MOCK_LLM:
        # Mock mode (graded baseline): keyword heuristic, no LLM call
        if any(keyword in query_lower for keyword in POLICY_KEYWORDS):
            intent = "policy_question"
        else:
            intent = "general_question"
    else:
        # Optional MOCK_LLM=0 extension: call the LLM to classify instead
        intent = "policy_question"  # placeholder for the real-LLM path

    return {**state, "intent": intent}


def retrieve_and_answer(state: GraphState) -> GraphState:
    query = state["query"]
    query_embedding = embed_model.encode([query]).tolist()

    results = collection.query(query_embeddings=query_embedding, n_results=3)
    retrieved_ids = results["ids"][0]
    retrieved_docs = results["documents"][0]

    top_chunk = retrieved_docs[0]
    top_chunk_snippet = top_chunk[:200]

    if MOCK_LLM:
        # Mock mode (graded baseline): canned templated answer, no LLM call
        answer = f"Based on the retrieved context: {top_chunk_snippet}"
        confidence = 1.0
    else:
        # Optional MOCK_LLM=0 extension: prompt the real LLM using the structured
        # template, grounded only in the retrieved chunks
        context = "\n".join(retrieved_docs)
        prompt = PROMPT_TEMPLATE.format(context=context, question=query)
        answer = "[real-LLM answer would go here]"  # placeholder for the real-LLM path
        confidence = 0.9

    return {**state, "answer": answer, "sources": list(retrieved_ids), "confidence": confidence}


def direct_answer(state: GraphState) -> GraphState:
    if MOCK_LLM:
        # Mock mode (graded baseline): fixed canned string, no LLM call
        answer = "I can only answer questions about Zepto policies right now."
    else:
        # Optional MOCK_LLM=0 extension: prompt the LLM directly, no retrieval
        answer = "[real-LLM direct answer would go here]"  # placeholder

    return {**state, "answer": answer, "sources": [], "confidence": 1.0}


def route_by_intent(state: GraphState) -> str:
    if state["intent"] == "policy_question":
        return "retrieve_and_answer"
    else:
        return "direct_answer"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", retrieve_and_answer)
    graph.add_node("direct_answer", direct_answer)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "retrieve_and_answer": "retrieve_and_answer",
            "direct_answer": "direct_answer"
        }
    )

    graph.add_edge("retrieve_and_answer", END)
    graph.add_edge("direct_answer", END)

    return graph.compile()


app_graph = build_graph()


if __name__ == "__main__":
    # Quick manual test — one policy question, one general question
    test_queries = [
        "How long does delivery take?",
        "What's the weather like today?"
    ]
    for q in test_queries:
        result = app_graph.invoke({"query": q, "intent": "", "answer": "", "sources": [], "confidence": 0.0})
        print(f"Query: {q}")
        print(f"Intent: {result['intent']}")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
        print(f"Confidence: {result['confidence']}")
        print()