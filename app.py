from fastapi import FastAPI, Path, Body, HTTPException
from uuid import uuid4
import redis
from sentence_transformers import SentenceTransformer
import requests
import json
import gzip
import os
import sys
import base64
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gemma_agent 

app = FastAPI()

# Conexion a Redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
except redis.RedisError as e:
    raise Exception(f"Redis connection failed: {str(e)}")

# Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# modelo de Embeddings 
embedding_model = SentenceTransformer('all-MiniLM-L12-v2', device='cpu')

# carga el archivo beers.json.gz y genera los embeddings
def load_embeddings():
    try:
        with gzip.open('data/beers.json.gz', 'rt') as f:
            beers = json.load(f)
        for beer in beers:
            key = f"beer:{beer['id']}"
            # Verifica si ya existe el par key:value para evitar duplicados
            if not r.exists(key):
                content = f"Name: {beer['name']} Description: {beer['description']}"
                embedding = embedding_model.encode(content)
                embedding_bytes = embedding.tobytes()
                embedding_b64 = base64.b64encode(embedding_bytes).decode('utf-8')
                r.set(key, embedding_b64)
        return {"message": f"Loaded {len(beers)} beers into Redis"}
    except FileNotFoundError:
        raise Exception("beers.json.gz not found in data directory")
    except Exception as e:
        raise Exception(f"Error loading embeddings: {str(e)}")

# modelo de inferencia usando la api de Ollama
def generate_text(prompt):
    payload = {
        "model": "gemma3:270m",
        "prompt": prompt,
        "temperature": 0.2,
        "max_tokens": 512
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True, timeout=30)
        response.raise_for_status()
        full_response = ""
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line.decode('utf-8'))
                if 'response' in json_response:
                    full_response += json_response['response']
                if json_response.get('done', False):
                    break
        return full_response
    except requests.Timeout:
        return "Error: Ollama API request timed out"
    except requests.RequestException as e:
        return f"Error calling Ollama API: {str(e)}"

# Inicializacion del agente en C++
try:
    agent = gemma_agent.BeerRAGAgent('config.json', generate_text)
except Exception as e:
    raise Exception(f"Failed to initialize BeerRAGAgent: {str(e)}")

@app.post("/chat/startChat")
def start_chat():
    return {"message": str(uuid4())}

@app.post("/chat/{chatId}")
def chat_message(chatId: str = Path(...), prompt: dict = Body(...)):
    message = prompt.get('prompt')
    if not message:
        raise HTTPException(status_code=400, detail="La pregunta u orden es requerida")
    response = agent.generate_response(message)
    return {"message": response}

"""
@app.post("/documents/upload")
def upload_document(doc: str = Body(...)):
    return {"message": "Document upload not supported"}
"""

@app.post("/load_embeddings")
def trigger_load_embeddings():
    try:
        result = load_embeddings()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)