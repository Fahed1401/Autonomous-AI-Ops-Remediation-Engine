import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. Initialize the embedding model (runs locally on your Mac M2)
print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def ingest_documents():
    # 2. Load the SOP document
    file_path = "company_docs/SOP_Security_Incident_Response.md"
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        return

    loader = TextLoader(file_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} document(s).")

    # 3. Split the document into smaller chunks for the AI to digest easily
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, 
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split document into {len(chunks)} chunks.")

    # 4. Create the ChromaDB vector store and save it locally
    db_directory = "./chroma_db"
    print("Embedding chunks and saving to ChromaDB...")
    
    vector_store = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=db_directory
    )
    
    print(f"Success! Vector database saved locally in the '{db_directory}' folder.")

if __name__ == "__main__":
    ingest_documents()