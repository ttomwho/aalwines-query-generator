import json
from tqdm import tqdm
import os
import numpy as np
import pickle
import faiss
from typing import List, Dict, Any
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise EnvironmentError("❌ OPENAI_API_KEY is not set or not found in .env")

client = OpenAI(api_key=api_key)

sys.stdout.reconfigure(encoding='utf-8')

# OpenAI Client
client = OpenAI()

# --- EMBEDDINGS ---
def load_embeddings_dict(path: str) -> Dict[str, List[float]]:
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_embeddings_dict(path: str, data: Dict[str, List[float]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)

def get_openai_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    try:
        response = client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[!] get_openai_embedding() failed: {e}")
        raise


def embed_examples(chunks: List[str], cache_file: str = "embeddings/cache.json", model: str = "text-embedding-3-small") -> List[Dict]:
    embedded = []
    cache = load_embeddings_dict(cache_file)
    updated = False
    for chunk in tqdm(chunks, desc="Embedding chunks"):
        if chunk in cache:
            embedding = cache[chunk]
        else:
            embedding = get_openai_embedding(chunk, model)
            cache[chunk] = embedding
            updated = True

        embedded.append({"text": chunk, "embedding": embedding, "meta": chunk})

    if updated:
        save_embeddings_dict(cache_file, cache)

    return embedded

# --- FAISS ---
def store_embeddings_in_faiss(
    embedded_chunks: List[Dict[str, Any]], 
    index_path: str = "results/faiss_index.index", 
    metadata_path: str = "results/faiss_metadata.pkl"
):
    if not embedded_chunks:
        raise ValueError("No embeddings provided to store in FAISS.")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(index_path), exist_ok=True)


    first_vec = np.array(embedded_chunks[0]["embedding"], dtype=np.float32)
    dim = first_vec.shape[0]
    index = faiss.IndexFlatL2(dim)

    embeddings = [np.array(entry["embedding"], dtype=np.float32) for entry in embedded_chunks]
    metadata = [entry["meta"] for entry in embedded_chunks]

    embeddings_np = np.vstack(embeddings)
    index.add(embeddings_np)

    faiss.write_index(index, index_path)
    with open(metadata_path, "wb") as f:
        pickle.dump(metadata, f)


def search(query_text: str, model: str = "text-embedding-3-small", index_path: str = "results/faiss_index.index", metadata_path: str = "results/faiss_metadata.pkl", k: int = 5) -> List[Dict[str, Any]]:
    try:
        index = faiss.read_index(index_path)
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)

        query_embedding = np.array([get_openai_embedding(query_text, model)], dtype=np.float32)
        D, I = index.search(query_embedding, k)
        return [metadata[i] for i in I[0] if 0 <= i < len(metadata)]
    
    except Exception as e:
        print(f"[!] search() error: {e}")
        raise

# --- EXAMPLES ---
def load_examples2(filepath="run/examples.txt"):
    examples = []
    with open(filepath, "r", encoding="utf-8") as f:
        current_nl = ""
        current_regex = ""
        for line in f:
            line = line.strip()
            if line.startswith("Input:"):
                current_nl = f"{line.strip()} "
            elif line.startswith("REGEX:"):
                current_regex = line.strip()
                examples.append((current_nl, current_regex))
                current_nl, current_regex = "", ""

    return examples
