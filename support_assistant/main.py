from fastapi import FastAPI
from schema import AskRequest, AskResponse
from graph import app_graph

app = FastAPI(title="Zepto Support Assistant")


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    result = app_graph.invoke({
        "query": request.query,
        "intent": "",
        "answer": "",
        "sources": [],
        "confidence": 0.0
    })
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"]
    )