"""
backend/rag_router.py
FastAPI router exposing the /chat endpoint for the RAG chatbot.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from .rag import ask_rag

router = APIRouter(prefix="/chat", tags=["RAG Chatbot"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Ask a question about the Onekey platform (users, API keys, usage logs).
    The RAG system queries NeonDB and answers in plain English via Groq LLM.
    """
    if not req.question.strip():
        return ChatResponse(answer="Please ask me something!")
    answer = ask_rag(req.question.strip())
    return ChatResponse(answer=answer)
