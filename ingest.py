import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from database import get_collection, get_db
from models import Document
import os
import threading
import queue
import hashlib
import re
import datetime

# --- Global Ingestion Queue & State ---
ingest_queue = queue.Queue()

INGESTION_STATE = {
    "is_active": False,
    "total_files": 0,
    "processed_files": 0,
    "current_file": "",
    "message": ""
}

def worker():
    """Single background worker to process files sequentially."""
    while True:
        task = ingest_queue.get()
        if task is None: break
        
        INGESTION_STATE["is_active"] = True
        INGESTION_STATE["current_file"] = os.path.basename(task['path'])
        INGESTION_STATE["message"] = "Processing"
        
        try:
            if task['type'] == 'pdf':
                _process_pdf(task['path'], task['campaign_id'], task['category'])
            elif task['type'] == 'txt':
                _process_text(task['path'], task['campaign_id'], task['category'])
            elif task['type'] == 'url':
                if 'docs.google.com/document/d/' in task['path']:
                    _process_google_doc(task['path'], task['campaign_id'], task['category'])
                else:
                    _process_url(task['path'], 10, task['campaign_id'], task['category'])
            elif task['type'] == 'google_doc':
                _process_google_doc(task['path'], task['campaign_id'], task['category'])
        except Exception as e:
            print(f"Error processing {task['path']}: {e}")
            
        INGESTION_STATE["processed_files"] += 1
        ingest_queue.task_done()
        
        if ingest_queue.empty():
            INGESTION_STATE["is_active"] = False
            INGESTION_STATE["message"] = "Ingestion complete."

# Start the worker thread
threading.Thread(target=worker, daemon=True).start()

def add_to_queue(file_path: str, file_type: str, campaign_id: int = None, category: str = "Uncategorized"):
    # Reset counters if queue was previously empty/finished
    if not INGESTION_STATE["is_active"] and ingest_queue.empty():
        INGESTION_STATE["total_files"] = 0
        INGESTION_STATE["processed_files"] = 0
        
    INGESTION_STATE["total_files"] += 1
    INGESTION_STATE["is_active"] = True
    ingest_queue.put({"path": file_path, "type": file_type, "campaign_id": campaign_id, "category": category})

def ingest_directory_scan(directory_path: str, campaign_id: int = None, category: str = "Uncategorized"):
    print(f"Scanning directory: {directory_path}")
    count = 0
    for root, _, files in os.walk(directory_path):
        for file in files:
            path = os.path.join(root, file)
            if file.lower().endswith('.pdf'):
                add_to_queue(path, 'pdf', campaign_id, category)
                count += 1
            elif file.lower().endswith(('.txt', '.md')):
                add_to_queue(path, 'txt', campaign_id, category)
                count += 1
    return count

# --- Core Processors (Synchronous) ---
def _process_pdf(file_path: str, campaign_id: int = None, category: str = "Uncategorized"):
    print(f"Ingesting PDF: {file_path}")
    doc = fitz.open(file_path)
    chunks, metadata, ids = [], [], []
    for page_num in range(len(doc)):
        text = doc.load_page(page_num).get_text()
        if text.strip():
            chunks.append(text)
            metadata.append({"source": file_path, "page": page_num + 1, "category": category})
            ids.append(f"{file_path}_page_{page_num+1}")
            
    if chunks:
        collection_name = f"campaign_{campaign_id}_lore" if campaign_id else "global_rules"
        get_collection(collection_name).add(documents=chunks, metadatas=metadata, ids=ids)
        db = next(get_db())
        # Avoid duplicate database entries
        existing = db.query(Document).filter_by(campaign_id=campaign_id, source_path=file_path).first()
        if not existing:
            db.add(Document(campaign_id=campaign_id, title=os.path.basename(file_path), source_type="pdf", source_path=file_path, category=category))
            db.commit()

def _process_text(file_path: str, campaign_id: int = None, category: str = "Uncategorized"):
    print(f"Ingesting Text: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    chunks = [c.strip() for c in text.split('\n\n') if c.strip()]
    metadata = [{"source": file_path, "category": category} for _ in chunks]
    ids = [f"{file_path}_{i}" for i in range(len(chunks))]
    
    if chunks:
        collection_name = f"campaign_{campaign_id}_lore" if campaign_id else "global_rules"
        get_collection(collection_name).add(documents=chunks, metadatas=metadata, ids=ids)
        db = next(get_db())
        existing = db.query(Document).filter_by(campaign_id=campaign_id, source_path=file_path).first()
        if not existing:
            db.add(Document(campaign_id=campaign_id, title=os.path.basename(file_path), source_type="txt", source_path=file_path, category=category))
            db.commit()

def _process_url(base_url: str, max_pages: int = 10, campaign_id: int = None, category: str = "Uncategorized"):
    print(f"Starting crawl at: {base_url}")
    visited, to_visit = set(), [base_url]
    domain = urlparse(base_url).netloc
    chunks, metadata, ids = [], [], []
    
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited: continue
        
        try:
            response = requests.get(url, timeout=5)
            visited.add(url)
            if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                soup = BeautifulSoup(response.text, 'html.parser')
                for element in soup(["script", "style", "nav", "footer", "header"]): element.decompose()
                text = soup.get_text(separator=' ', strip=True)
                if text:
                    chunks.append(text)
                    metadata.append({"source": url, "category": category})
                    ids.append(url)
                for link in soup.find_all('a', href=True):
                    next_url = urljoin(base_url, link['href'])
                    if urlparse(next_url).netloc == domain and next_url not in visited:
                        to_visit.append(next_url)
        except Exception as e: print(f"Error fetching {url}: {e}")
            
    if chunks:
        collection_name = f"campaign_{campaign_id}_lore" if campaign_id else "global_rules"
        get_collection(collection_name).add(documents=chunks, metadatas=metadata, ids=ids)
        db = next(get_db())
        existing = db.query(Document).filter_by(campaign_id=campaign_id, source_path=base_url).first()
        if not existing:
            db.add(Document(campaign_id=campaign_id, title=base_url, source_type="url", source_path=base_url, category=category))
            db.commit()

def _process_google_doc(url: str, campaign_id: int = None, category: str = "Uncategorized"):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not match: return
    
    doc_id = match.group(1)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    
    try:
        response = requests.get(export_url, timeout=10)
        response.raise_for_status()
        text = response.text
    except Exception as e:
        print(f"Failed to fetch Google Doc: {e}")
        return
        
    current_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    db = next(get_db())
    
    existing = db.query(Document).filter_by(campaign_id=campaign_id, source_path=url).first()
    if existing and existing.content_hash == current_hash:
        existing.last_synced_at = datetime.datetime.utcnow()
        db.commit()
        return

    print(f"Ingesting/Updating Google Doc: {url}")
    chunks = [c.strip() for c in text.split('\n\n') if c.strip()]
    metadata = [{"source": url, "category": category} for _ in chunks]
    ids = [f"gdoc_{doc_id}_{i}" for i in range(len(chunks))]
    
    collection_name = f"campaign_{campaign_id}_lore" if campaign_id else "global_rules"
    collection = get_collection(collection_name)
    
    if existing:
        try: collection.delete(where={"source": url})
        except: pass
        
    if chunks:
        collection.add(documents=chunks, metadatas=metadata, ids=ids)
        if not existing:
            new_doc = Document(campaign_id=campaign_id, title=f"Google Doc ({doc_id})", source_type="google_doc", source_path=url, category=category, content_hash=current_hash, last_synced_at=datetime.datetime.utcnow())
            db.add(new_doc)
        else:
            existing.content_hash = current_hash
            existing.last_synced_at = datetime.datetime.utcnow()
        db.commit()

