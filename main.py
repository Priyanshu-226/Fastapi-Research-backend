from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from utils import process_document, get_answer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryModel(BaseModel):
    question: str

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    os.makedirs("temp_files", exist_ok=True)
    temp_path = f"temp_files/{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    process_document(temp_path)
    return {"status": "File uploaded and processed"}

@app.post("/ask")
async def ask_question(query: QueryModel):
    answer = get_answer(query.question)
    return {"answer": answer}

@app.get("/")
def read_root():
    return {"message": "Research backend is live!"}