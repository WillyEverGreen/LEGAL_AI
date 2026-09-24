import os
import re

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

os.environ["TOKENIZERS_PARALLELISM"] = "false" # Prevent deadlock

import pathlib

from dotenv import load_dotenv
from rag_engine import RAGEngine

# Load .env from parent directory (root of project)
base_path = pathlib.Path(__file__).parent.parent
load_dotenv(dotenv_path=base_path / ".env")

app = FastAPI(title="LegalAi RAG Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = None

@app.on_event("startup")
async def startup_event():
    global engine
    print("[Main] Initializing RAG Engine...", flush=True)
    engine = RAGEngine()
    print("[Main] RAG Engine Initialized", flush=True)

class QueryRequest(BaseModel):
    query: str
    language: str = "en"
    domain: str = "all"
    arguments_mode: bool = False
    analysis_mode: bool = False
    session_id: str = None  # NEW: For conversation memory

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"status": "ok", "service": "RAG Service"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "healthy"}

class DraftRequest(BaseModel):
    draft_type: str
    details: str
    language: str = "en"

@app.post("/draft")
async def generate_draft(request: DraftRequest):
    try:
        print(f"[Main] Drafting request received: {request.draft_type} in {request.language}", flush=True)
        draft_text = engine.generate_draft(
            draft_type=request.draft_type,
            details=request.details,
            language=request.language
        )
        return {"draft": draft_text}
    except Exception as e:
        print(f"[Main] Error generating draft: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_rag(request: QueryRequest):
    try:
        # Fast path strictly for standalone greetings / thanks
        query_lower = request.query.lower().strip()
        clean_q = re.sub(r'[^\w\s]', '', query_lower).strip()

        standalone_greetings = {'hello', 'hi', 'hey', 'namaste', 'pranam', 'halo', 'good morning', 'good afternoon', 'good evening'}
        standalone_thanks = {'thank you', 'thanks', 'dhanyavad', 'shukriya'}
        standalone_meta = {'who are you', 'your name', 'about you', 'kaun ho', 'tumhara naam'}

        if clean_q in standalone_greetings:
            if request.language == 'hi':
                return {
                    "answer": "नमस्ते! मैं **LegalAi** हूँ — आपका भारतीय कानूनी अनुसंधान सहायक। मैं भारतीय कानून (BNS/IPC), कानूनी दस्तावेज़ ड्राफ्टिंग, और विधिक सलाह में आपकी सहायता कर सकता हूँ।\n\nआज मैं आपकी कैसे मदद कर सकता हूँ?",
                    "citations": [],
                    "related_judgments": []
                }
            else:
                return {
                    "answer": "Hello! I'm **LegalAi** — your AI assistant for Indian legal research. I can assist with Indian laws (BNS/IPC), statutory comparisons, contract drafting, and legal queries.\n\nHow can I help you today?",
                    "citations": [],
                    "related_judgments": []
                }
        elif clean_q in standalone_thanks:
            if request.language == 'hi':
                return {
                    "answer": "आपका स्वागत है! यदि आपके पास कोई अन्य कानूनी प्रश्न या विषय है, तो बेझिझक पूछें।",
                    "citations": [],
                    "related_judgments": []
                }
            else:
                return {
                    "answer": "You're very welcome! Feel free to ask if you have more legal questions or need assistance with Indian law.",
                    "citations": [],
                    "related_judgments": []
                }
        elif clean_q in standalone_meta:
            if request.language == 'hi':
                return {
                    "answer": "मैं **LegalAi** हूँ, एक अत्यंत तीव्र AI कानूनी अनुसंधान सहायक। मुझे भारतीय कानून (IPC/BNS, CrPC/BNSS, IT Act, Companies Act) और विधिक ड्राफ्टिंग के लिए प्रशिक्षित किया गया है।",
                    "citations": [],
                    "related_judgments": []
                }
            else:
                return {
                    "answer": "I am **LegalAi**, an ultra-fast AI legal intelligence assistant specialized in Indian jurisprudence (IPC/BNS transitions, CrPC/BNSS, IT Act, corporate laws) and legal document drafting.",
                    "citations": [],
                    "related_judgments": []
                }
        
        # Add user message to conversation memory if session exists
        if request.session_id:
            engine.conversation_memory.add_message(request.session_id, "user", request.query)
        
        response = await engine.query(
            request.query, 
            request.language, 
            request.arguments_mode, 
            request.analysis_mode,
            request.session_id  # Pass session_id to engine
        )
        
        # Add assistant response to conversation memory
        if request.session_id and "answer" in response:
            engine.conversation_memory.add_message(request.session_id, "assistant", response["answer"])
        
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize")
async def handle_summarize(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    try:
        content = await file.read()
        summary = await engine.summarize(content, file.filename)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CompareRequest(BaseModel):
    text1: str
    text2: str

@app.post("/compare")
async def handle_compare(request: CompareRequest):
    try:
        comparison = await engine.compare_clauses(request.text1, request.text2)
        return {"comparison": comparison}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Session Management Endpoints
@app.post("/session/create")
async def create_session():
    """Create a new conversation session"""
    try:
        session_id = engine.conversation_memory.create_session()
        return {"session_id": session_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/clear")
async def clear_session(session_id: str):
    """Clear conversation history for a session"""
    try:
        engine.conversation_memory.clear_session(session_id)
        return {"session_id": session_id, "status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str, max_messages: int = 10):
    """Get conversation history for a session"""
    try:
        history = engine.conversation_memory.get_history(session_id, max_messages)
        metadata = engine.conversation_memory.get_session_info(session_id)
        return {"session_id": session_id, "history": history, "metadata": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session"""
    try:
        engine.conversation_memory.delete_session(session_id)
        return {"session_id": session_id, "status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=300)
