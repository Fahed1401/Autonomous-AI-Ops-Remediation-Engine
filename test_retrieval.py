import json
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. Load the same embedding model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Connect to the local ChromaDB database we just created
db_directory = "./chroma_db"
vector_store = Chroma(persist_directory=db_directory, embedding_function=embeddings)

def test_rag_retrieval():
    # 3. Read the fake cloud alert from Phase 1
    try:
        with open('cloud_alert.json', 'r') as f:
            alert_data = json.load(f)
    except FileNotFoundError:
        print("Error: cloud_alert.json not found. Run generate_alert.py first.")
        return

    # Extract the description of the problem
    search_query = alert_data["description"]
    print(f"\n🚨 ALERT RECEIVED: {search_query}")
    print("-" * 50)
    
    # 4. Perform a Semantic Similarity Search against the Vector Database
    print("🔍 Searching internal SOPs for a solution...\n")
    results = vector_store.similarity_search(search_query, k=1) # k=1 returns the single best match

    if results:
        print("✅ RELEVANT SOP FOUND:")
        print(results[0].page_content)
        print("-" * 50)
        print(f"Source file: {results[0].metadata['source']}")
    else:
        print("❌ No relevant SOPs found in the database.")

if __name__ == "__main__":
    test_rag_retrieval()