import os
import shutil
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
import threading
import time
from database import get_collection, get_db, SessionLocal
from models import Campaign, Document
from ingest import add_to_queue, ingest_directory_scan, INGESTION_STATE

def google_doc_poller():
    while True:
        try:
            db = SessionLocal()
            try:
                docs = db.query(Document).filter_by(source_type="google_doc").all()
                for d in docs:
                    add_to_queue(d.source_path, 'google_doc', d.campaign_id, d.category)
            finally:
                db.close()
        except Exception as e:
            print("Poller error:", e)
        time.sleep(60)

threading.Thread(target=google_doc_poller, daemon=True).start()

app = FastAPI(title="AI DM Assistant API")

# --- LLM Provider Interface ---
class LLMProvider:
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def query(self, prompt: str) -> str:
        if self.provider == "openrouter":
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]}
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        elif self.provider == "ollama":
            response = requests.post(
                url="http://localhost:11434/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False}
            )
            return response.json()['response']
        else:
            raise ValueError(f"Unknown provider {self.provider}")

from typing import Optional

class QueryRequest(BaseModel):
    campaign_id: Optional[int] = None
    question: str
    provider: str = "openrouter"
    api_key: str = ""
    model: str = "anthropic/claude-3.5-sonnet"

class LookaheadRequest(BaseModel):
    campaign_id: Optional[int] = None
    text: str
    provider: str = "openrouter"
    api_key: str = ""
    model: str = "anthropic/claude-3.5-sonnet"

class CampaignCreate(BaseModel):
    name: str
    description: str = ""

class UrlIngestRequest(BaseModel):
    url: str
    campaign_id: Optional[int] = None
    category: str = "Uncategorized"

class DirectoryIngestRequest(BaseModel):
    directory_path: str
    campaign_id: Optional[int] = None
    category: str = "Uncategorized"

class CategoryUpdateRequest(BaseModel):
    category: str

# --- Endpoints ---
@app.get("/api/campaigns")
def list_campaigns(db = Depends(get_db)):
    campaigns = db.query(Campaign).all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in campaigns]

@app.post("/api/campaigns")
def create_campaign(req: CampaignCreate, db = Depends(get_db)):
    new_camp = Campaign(name=req.name, description=req.description)
    db.add(new_camp)
    db.commit()
    db.refresh(new_camp)
    return {"id": new_camp.id, "name": new_camp.name}

@app.get("/api/ingest/status")
def get_ingest_status():
    return INGESTION_STATE

@app.get("/api/documents")
def list_documents(campaign_id: int = None, db = Depends(get_db)):
    if campaign_id:
        docs = db.query(Document).filter_by(campaign_id=campaign_id).all()
    else:
        docs = db.query(Document).filter_by(campaign_id=None).all()
    return [{"id": d.id, "title": d.title, "type": d.source_type, "url": f"/uploads/{os.path.basename(d.source_path)}" if not d.source_path.startswith("http") else d.source_path, "category": d.category} for d in docs]

@app.get("/api/documents/all")
def list_all_documents(db = Depends(get_db)):
    docs = db.query(Document).all()
    return [{"id": d.id, "title": d.title, "type": d.source_type, "url": f"/uploads/{os.path.basename(d.source_path)}" if not d.source_path.startswith("http") else d.source_path, "category": d.category, "campaign_id": d.campaign_id} for d in docs]

@app.put("/api/documents/{doc_id}/category")
def update_document_category(doc_id: int, req: CategoryUpdateRequest, db = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.category = req.category
    db.commit()
    return {"message": "Category updated successfully"}

@app.post("/api/ingest/file")
async def api_ingest_file(file: UploadFile = File(...), campaign_id: int = Form(None), category: str = Form("Uncategorized")):
    os.makedirs("scratch_uploads", exist_ok=True)
    file_path = os.path.join("scratch_uploads", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    if file.filename.lower().endswith('.pdf'):
        add_to_queue(file_path, 'pdf', campaign_id, category)
    elif file.filename.lower().endswith(('.txt', '.md')):
        add_to_queue(file_path, 'txt', campaign_id, category)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    return {"message": f"Queued {file.filename}"}

@app.post("/api/ingest/directory")
def api_ingest_directory(req: DirectoryIngestRequest):
    if not os.path.isdir(req.directory_path):
        raise HTTPException(status_code=400, detail="Invalid directory path")
    count = ingest_directory_scan(req.directory_path, req.campaign_id, req.category)
    return {"message": f"Queued {count} files from directory."}

@app.post("/api/ingest/url")
def api_ingest_url(req: UrlIngestRequest):
    add_to_queue(req.url, 'url', req.campaign_id, req.category)
    return {"message": f"Queued {req.url}"}

@app.post("/api/query")
def handle_query(req: QueryRequest):
    contexts, raw_sources = [], []
    
    global_results = get_collection("global_rules").query(query_texts=[req.question], n_results=3)
    if global_results['documents'] and global_results['documents'][0]:
        contexts.extend(global_results['documents'][0])
        raw_sources.extend(global_results['metadatas'][0])

    if req.campaign_id:
        try:
            campaign_results = get_collection(f"campaign_{req.campaign_id}_lore").query(query_texts=[req.question], n_results=3)
            if campaign_results['documents'] and campaign_results['documents'][0]:
                contexts.extend(campaign_results['documents'][0])
                raw_sources.extend(campaign_results['metadatas'][0])
        except Exception:
            pass 
            
    formatted_sources = []
    seen = set()
    for meta in raw_sources:
        src = meta.get('source', 'Unknown')
        page = meta.get('page')
        
        identifier = f"{src}_{page}" if page else src
        if identifier in seen: continue
        seen.add(identifier)
        
        if src.startswith('http'):
            formatted_sources.append({"name": src, "url": src})
        else:
            basename = os.path.basename(src)
            url = f"/uploads/{basename}"
            if page:
                url += f"#page={page}"
                formatted_sources.append({"name": f"{basename} (Page {page})", "url": url})
            else:
                formatted_sources.append({"name": basename, "url": url})
            
    context_text = "\n\n---\n\n".join(contexts)
    prompt = f"You are an expert Dungeon Master Assistant for the Pathfinder RPG.\nUse the provided Reference Text to help answer the user's question. If the user provides a quote or text in their question, analyze it directly.\n\nReference Text:\n{context_text}\n\nQuestion:\n{req.question}"
    
    print("\n" + "="*50)
    print("SENDING PROMPT TO ORACLE:")
    print("="*50)
    print(prompt)
    print("="*50 + "\n")

    try:
        llm = LLMProvider(req.provider, req.api_key, req.model)
        answer = llm.query(prompt)
        return {"answer": answer, "sources": formatted_sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import json
import re

@app.post("/api/lookahead")
def handle_lookahead(req: LookaheadRequest):
    prompt = f"""You are an expert Dungeon Master Assistant.
Analyze the following page text from a Pathfinder module and extract a list of mechanically significant named entities.
Include specific Monsters, prominent NPCs, unique Spells, and specific Magic Items mentioned.
Do NOT include generic terms like 'sword', 'door', 'PC', or 'DC 15'.
Return ONLY a valid JSON array of strings representing these entities, e.g. ["Elder Ice Elemental", "Queen Elvanna"].

Text to analyze:
{req.text[:2000]}
"""
    try:
        llm = LLMProvider(req.provider, req.api_key, req.model)
        answer = llm.query(prompt)
        
        try:
            match = re.search(r'\[.*\]', answer.replace('\n', ''))
            if match:
                entities = json.loads(match.group(0))
            else:
                entities = json.loads(answer)
        except Exception:
            entities = []
            
        results = []
        for entity in entities:
            contexts, raw_sources = [], []
            global_results = get_collection("global_rules").query(query_texts=[entity], n_results=1)
            if global_results['documents'] and global_results['documents'][0]:
                contexts.extend(global_results['documents'][0])
                raw_sources.extend(global_results['metadatas'][0])

            if req.campaign_id:
                try:
                    campaign_results = get_collection(f"campaign_{req.campaign_id}_lore").query(query_texts=[entity], n_results=1)
                    if campaign_results['documents'] and campaign_results['documents'][0]:
                        contexts.extend(campaign_results['documents'][0])
                        raw_sources.extend(campaign_results['metadatas'][0])
                except Exception:
                    pass
            
            if contexts:
                results.append({
                    "entity": entity,
                    "snippet": contexts[0][:300] + "...",
                    "source": os.path.basename(raw_sources[0].get('source', 'Unknown')) if raw_sources else "Unknown"
                })
                
        return {"entities": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class LookupRequest(BaseModel):
    query: str
    provider: str = "ollama"
    model: str = "mistral:instruct"

@app.post("/api/lookup")
def handle_lookup(req: LookupRequest):
    PROMPT = f"You are an expert Game Master. Provide the stat block summary (CR, HP, AC, Attacks, Special Abilities) for the RPG entity: {req.query}. Be concise."
    try:
        response = requests.post(
            url="http://localhost:11434/api/generate",
            json={
                "model": req.model, 
                "prompt": PROMPT, 
                "stream": False
            }
        )
        if response.status_code == 200:
            return {"result": response.json().get("response", "No response")}
        return {"result": f"Error: {response.text}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExtractRequest(BaseModel):
    text: str
    provider: str = "ollama"
    api_key: str = ""
    model: str = "mistral:instruct"

@app.post("/api/extract")
def handle_extract(req: ExtractRequest):
    SYSTEM_PROMPT = """You are an expert Game Master assistant. Your task is EXHAUSTIVE extraction. You must extract EVERY SINGLE SENTENCE from the text that matches these 7 categories. Do not skip any.

1. staging: Read-Aloud text, room dimensions, physical descriptions of the environment (e.g. "A wide window looks out...", "The floor of this cellar...").
2. npcs: Monster names, NPC names, and stat block references.
3. mechanics: DCs, saving throws, skill checks, and hidden triggers.
4. hazards: Environmental hazards, traps, and physical dangers.
5. lore: Lore, secrets, and background history.
6. loot: Treasure, gold, weapons, and magic items.
7. structure: DM plot structure, "Development" notes, and module progression.

Return ONLY a valid JSON object matching this exact schema. DO NOT include markdown formatting.
{
  "highlights": [
    {
      "exact_text_quote": "The exact sentence",
      "catId": "staging" | "npcs" | "mechanics" | "hazards" | "lore" | "loot" | "structure"
    }
  ]
}
"""
    prompt = f"{SYSTEM_PROMPT}\n\nPAGE TEXT:\n{req.text[:4000]}"
    try:
        if req.provider == "ollama":
            response = requests.post(
                url="http://localhost:11434/api/generate",
                json={
                    "model": req.model, 
                    "prompt": prompt, 
                    "stream": False, 
                    "format": "json",
                    "options": {"temperature": 0.1}
                },
                timeout=120
            )
            response.raise_for_status()
            result_text = response.json()['response']
        else:
            llm = LLMProvider(req.provider, req.api_key, req.model)
            result_text = llm.query(prompt)
            
        import re
        match = re.search(r'\{.*\}', result_text.replace('\n', ''))
        if match:
            return json.loads(match.group(0))
        return json.loads(result_text)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout - VRAM is likely full.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

os.makedirs("scratch_uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="scratch_uploads"), name="uploads")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
