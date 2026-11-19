import json
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. Connect to the local Vector Database (Chroma)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# 2. Initialize the local Llama 3 model via Ollama
print("Waking up Llama 3...")
llm = Ollama(model="llama3")

def generate_remediation_plan():
    # 3. Load the fake alert we generated in Phase 1
    try:
        with open('cloud_alert.json', 'r') as f:
            alert_data = json.load(f)
    except FileNotFoundError:
        print("Error: cloud_alert.json not found.")
        return
        
    alert_description = alert_data["description"]
    alert_resource = alert_data["affected_resource_id"]
    attacker_ip = alert_data["attacker_ip"]
    
    print(f"\n🚨 Analyzing Alert on Resource: {alert_resource}")
    
    # 4. Retrieve the exact SOP from ChromaDB
    results = vector_store.similarity_search(alert_description, k=1)
    if not results:
        print("❌ No SOP found. Cannot proceed safely.")
        return
    
    sop_context = results[0].page_content
    
    # 5. Build the Prompt (Instructing the AI on how to behave)
    template = """
    You are an autonomous Senior Cloud DevOps Engineer. 
    A critical security alert has been triggered in the cloud environment.
    
    Read the alert details and the retrieved internal company Standard Operating Procedure (SOP).
    Formulate a precise, step-by-step remediation plan to fix the issue.
    You must strictly follow the rules defined in the SOP.
    
    ALERT DETAILS:
    Description: {alert_description}
    Resource ID: {alert_resource}
    Attacker IP: {attacker_ip}
    
    COMPANY SOP:
    {sop_context}
    
    YOUR REMEDIATION PLAN:
    """
    
    prompt = PromptTemplate(
        input_variables=["alert_description", "alert_resource", "attacker_ip", "sop_context"],
        template=template
    )
    
    # 6. Chain the prompt to the LLM and execute
    print("🧠 Llama 3 is thinking... (This may take a few seconds on the first run)\n")
    chain = prompt | llm
    
    response = chain.invoke({
        "alert_description": alert_description,
        "alert_resource": alert_resource,
        "attacker_ip": attacker_ip,
        "sop_context": sop_context
    })
    
    print("✅ REMEDIATION PLAN GENERATED:")
    print("-" * 50)
    print(response)
    print("-" * 50)

if __name__ == "__main__":
    generate_remediation_plan()