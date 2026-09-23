import os
import pathlib
import requests
from dotenv import load_dotenv

base_path = pathlib.Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=base_path / ".env")

nvidia_key = os.getenv("NVIDIA_API_KEY")

def test_chat(key, model):
    if not key:
        print("Skipping NVIDIA Chat: Key not found in .env")
        return
    
    print(f"\n--- Testing NVIDIA NIM Chat ({model}) ---")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'NVIDIA NIM is working!'"}],
        "max_tokens": 30
    }
    
    try:
        response = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            print("[SUCCESS] Chat is WORKING!")
            print("Response:", response.json()['choices'][0]['message']['content'])
        else:
            print(f"[FAILED] Chat failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Chat error: {e}")

def test_embedding(key, model):
    if not key:
        print("Skipping NVIDIA Embedding: Key not found in .env")
        return
    
    print(f"\n--- Testing NVIDIA NIM Embedding ({model}) ---")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"input": ["Test legal embedding"], "model": model}
    
    try:
        response = requests.post("https://integrate.api.nvidia.com/v1/embeddings", headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            dim = len(response.json()['data'][0]['embedding'])
            print(f"[SUCCESS] Embeddings WORKING! (dimension: {dim})")
        else:
            print(f"[FAILED] Embedding failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Embedding error: {e}")

if __name__ == "__main__":
    test_chat(nvidia_key, "meta/llama-3.2-11b-vision-instruct")
    test_embedding(nvidia_key, "nvidia/nemotron-3-embed-1b")

