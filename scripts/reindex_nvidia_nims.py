import os
import pathlib
import sys
import time

import chromadb
import requests
from dotenv import load_dotenv

# Load environment
base_path = pathlib.Path(__file__).parent.parent
load_dotenv(dotenv_path=base_path / ".env")

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    print("❌ Error: NVIDIA_API_KEY not found in .env")
    sys.exit(1)

chroma_path = os.path.join(base_path, "rag_service", "chroma_db")
print(f"Connecting to ChromaDB at {chroma_path}...")
client = chromadb.PersistentClient(path=chroma_path)

# Source collection
try:
    src_coll = client.get_collection("legal_knowledge")
except Exception as e:
    print(f"❌ Error getting legal_knowledge collection: {e}")
    sys.exit(1)

data = src_coll.get()
total = len(data["ids"])
print(f"Found {total} documents in 'legal_knowledge'.")

# Destination collection
dest_name = "legal_knowledge_v2"
try:
    client.delete_collection(dest_name)
    print(f"Deleted existing '{dest_name}' collection for clean re-index.")
except Exception:
    pass

dest_coll = client.create_collection(name=dest_name)
print(f"Created new collection '{dest_name}'.")

BATCH_SIZE = 50
model_name = "nvidia/nemotron-3-embed-1b"
url = "https://integrate.api.nvidia.com/v1/embeddings"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

success_count = 0
for i in range(0, total, BATCH_SIZE):
    batch_ids = data["ids"][i:i + BATCH_SIZE]
    batch_docs = data["documents"][i:i + BATCH_SIZE]
    batch_metas = data["metadatas"][i:i + BATCH_SIZE]

    # Ensure documents are strings and non-empty
    cleaned_docs = [doc if (doc and doc.strip()) else "N/A" for doc in batch_docs]

    retries = 3
    embeddings = None
    for attempt in range(retries):
        try:
            payload = {
                "input": cleaned_docs,
                "model": model_name
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                result_data = resp.json()["data"]
                embeddings = [item["embedding"] for item in result_data]
                break
            else:
                print(f"⚠️ Batch {i//BATCH_SIZE + 1} attempt {attempt+1} failed: {resp.status_code} - {resp.text[:100]}")
                time.sleep(2)
        except Exception as ex:
            print(f"⚠️ Batch {i//BATCH_SIZE + 1} exception: {ex}")
            time.sleep(2)

    if embeddings:
        dest_coll.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=embeddings
        )
        success_count += len(batch_ids)
        print(f"[OK] [{success_count}/{total}] Ingested batch {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE}")
    else:
        print(f"[FAIL] Failed to get embeddings for batch starting at index {i}")

print(f"\nRe-indexing complete! '{dest_name}' now contains {dest_coll.count()} documents.")

# Verification query
print("\nTesting semantic retrieval on legal_knowledge_v2...")
test_query = "What is the punishment for murder under IPC and BNS?"
q_resp = requests.post(url, headers=headers, json={"input": [test_query], "model": model_name}, timeout=15)
if q_resp.status_code == 200:
    q_emb = [q_resp.json()["data"][0]["embedding"]]
    res = dest_coll.query(query_embeddings=q_emb, n_results=3)
    print("Top retrieved documents:")
    for rank, (doc_id, doc_meta) in enumerate(zip(res["ids"][0], res["metadatas"][0])):
        print(f"  {rank+1}. ID: {doc_id} | Law: {doc_meta.get('law', 'N/A')} | Section: {doc_meta.get('bns_section', doc_meta.get('ipc_section', 'N/A'))} | Topic: {doc_meta.get('topic', 'N/A')}")
else:
    print(f"Query embedding failed: {q_resp.text}")
