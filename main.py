from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
import shutil
from datetime import datetime
import asyncio
from pathlib import Path
import mimetypes

# Create FastAPI app
app = FastAPI(
    title="Research Tool API",
    description="Backend API for document upload and Q&A functionality",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for file storage
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory storage (in production, use a proper database)
documents_db = {}
chat_history = []

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    document_ids: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    confidence: float

class Document(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    upload_date: str
    status: str

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str

class ChatMessage(BaseModel):
    id: str
    message: str
    response: str
    sources: Optional[List[str]] = None
    timestamp: str

# Helper functions
def get_file_size(file_path: Path) -> int:
    return file_path.stat().st_size if file_path.exists() else 0

def get_content_type(filename: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"

async def process_document(document_id: str, file_path: Path):
    """Simulate document processing"""
    await asyncio.sleep(3)  # Simulate processing time
    
    if document_id in documents_db:
        documents_db[document_id]["status"] = "ready"
        print(f"Document {document_id} processed successfully")

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Research Tool API is running"}

@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.md', '.rtf'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Create file path
        file_path = UPLOAD_DIR / f"{document_id}_{file.filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Store document metadata
        document_data = {
            "id": document_id,
            "filename": file.filename,
            "size": get_file_size(file_path),
            "content_type": get_content_type(file.filename),
            "upload_date": datetime.now().isoformat(),
            "status": "processing",
            "file_path": str(file_path)
        }
        
        documents_db[document_id] = document_data
        
        # Start background processing
        asyncio.create_task(process_document(document_id, file_path))
        
        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="processing",
            message="Document uploaded successfully and is being processed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@app.get("/documents", response_model=List[Document])
async def get_documents():
    try:
        documents = []
        for doc_data in documents_db.values():
            documents.append(Document(
                id=doc_data["id"],
                filename=doc_data["filename"],
                size=doc_data["size"],
                content_type=doc_data["content_type"],
                upload_date=doc_data["upload_date"],
                status=doc_data["status"]
            ))
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        if document_id not in documents_db:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete file from filesystem
        doc_data = documents_db[document_id]
        file_path = Path(doc_data["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # Remove from database
        del documents_db[document_id]
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.get("/documents/{document_id}/content")
async def get_document_content(document_id: str):
    try:
        if document_id not in documents_db:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_data = documents_db[document_id]
        file_path = Path(doc_data["file_path"])
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found")
        
        # For text files, return content directly
        if doc_data["content_type"].startswith("text/"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content}
        else:
            return {"content": f"Binary file: {doc_data['filename']} ({doc_data['size']} bytes)"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document content: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Get ready documents
        ready_docs = [doc for doc in documents_db.values() if doc["status"] == "ready"]
        
        if not ready_docs and request.document_ids:
            return ChatResponse(
                response="I don't have any processed documents to analyze yet. Please wait for your documents to finish processing, or upload new documents.",
                sources=[],
                confidence=0.0
            )
        
        # Simulate AI response based on the message
        message = request.message.lower()
        
        # Generate contextual responses
        if "summarize" in message or "summary" in message:
            response = f"Based on your {len(ready_docs)} uploaded document(s), here's a summary: The documents contain valuable research information that can be analyzed for key insights, themes, and findings. The content appears to cover various topics that would benefit from deeper analysis."
        elif "key findings" in message or "findings" in message:
            response = f"Key findings from your {len(ready_docs)} document(s): 1) Important research data has been identified, 2) Multiple themes and patterns emerge from the content, 3) There are significant insights that warrant further investigation."
        elif "themes" in message or "theme" in message:
            response = f"Main themes identified across your {len(ready_docs)} document(s): Research methodology, data analysis, key conclusions, and recommendations for future work. These themes interconnect to form a comprehensive research narrative."
        elif "contradictions" in message or "contradiction" in message:
            response = f"After analyzing your {len(ready_docs)} document(s), I found some areas where different sources present varying perspectives on similar topics. These differences highlight the complexity of the research area and suggest areas for further investigation."
        elif "timeline" in message:
            response = f"Based on the chronological information in your {len(ready_docs)} document(s), here's a timeline of key events: The documents reference various time periods and developments that show the evolution of ideas and research in this field."
        else:
            response = f"I've analyzed your question about '{request.message}' in the context of your {len(ready_docs)} uploaded document(s). The information suggests several relevant points that address your inquiry. Would you like me to elaborate on any specific aspect?"
        
        # Get source filenames
        sources = [doc["filename"] for doc in ready_docs[:3]]  # Limit to first 3 sources
        
        # Store chat message
        chat_message = {
            "id": str(uuid.uuid4()),
            "message": request.message,
            "response": response,
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(chat_message)
        
        return ChatResponse(
            response=response,
            sources=sources,
            confidence=0.85
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat message: {str(e)}")

@app.get("/chat/history", response_model=List[ChatMessage])
async def get_chat_history():
    try:
        return [ChatMessage(**msg) for msg in chat_history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")

@app.delete("/chat/history")
async def clear_chat_history():
    try:
        global chat_history
        chat_history = []
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")

@app.post("/search")
async def search_documents(request: dict):
    try:
        query = request.get("query", "")
        document_ids = request.get("document_ids", [])
        
        # Filter documents based on IDs if provided
        search_docs = documents_db.values()
        if document_ids:
            search_docs = [doc for doc in documents_db.values() if doc["id"] in document_ids]
        
        # Simulate search results
        results = []
        for doc in search_docs:
            if doc["status"] == "ready":
                results.append({
                    "document_id": doc["id"],
                    "filename": doc["filename"],
                    "snippet": f"Search results for '{query}' found in {doc['filename']}...",
                    "relevance_score": 0.8
                })
        
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
