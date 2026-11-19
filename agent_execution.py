import json
import boto3
from langchain_community.llms import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool

# ==========================================
# 1. DEFINE THE AI'S TOOL (The Boto3 Action)
# ==========================================
# We expose this tool as a Python function decorated with LangChain's @tool annotation.
@tool
def revoke_ssh_access(security_group_id: str) -> str:
    """Useful for blocking unauthorized SSH (port 22) access on an AWS Security Group."""
    
    print(f"\n[🤖 AGENT TOOL TRIGGERED] Requesting to modify Security Group: {security_group_id}")
    
    # Human-in-the-Loop Checkpoint [cite: 345]
    print("\n" + "!"*50)
    print("⚠️  HUMAN-IN-THE-LOOP AUTHORIZATION REQUIRED ⚠️")
    print("!"*50)
    confirmation = input(f"The AI Agent wants to execute 'revoke_security_group_ingress' on {security_group_id} for Port 22.\nDo you approve this action? (Y/N): ")
    
    if confirmation.lower() != 'y':
        return "Action was cancelled by the human administrator. Stop executing."

    # If approved, execute the Boto3 command against LocalStack [cite: 165, 340]
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1', endpoint_url='http://localhost:4566')
        ec2.revoke_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        return f"SUCCESS: Revoked global SSH access on {security_group_id}."
    except Exception as e:
        return f"ERROR: Failed to modify security group: {str(e)}"

def run_autonomous_agent():
    # ==========================================
    # 2. LOAD INFRASTRUCTURE (Memory & Brain)
    # ==========================================
    print("Initializing Database and Llama 3...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_store = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    
    llm = Ollama(model="llama3")

    # ==========================================
    # 3. GET THE ALERT & SOP
    # ==========================================
    try:
        with open('cloud_alert.json', 'r') as f:
            alert_data = json.load(f)
    except FileNotFoundError:
        print("Error: cloud_alert.json not found.")
        return

    alert_desc = alert_data["description"]
    sg_id = alert_data["affected_resource_id"]
    
    print(f"\n🚨 ALERT DETECTED: {alert_desc} on {sg_id}")
    
    results = vector_store.similarity_search(alert_desc, k=1)
    sop_context = results[0].page_content if results else "No SOP found."

    # ==========================================
    # 4. ORCHESTRATE THE AGENT
    # ==========================================
    # Equip the agent with our Boto3 tool
    tools = [revoke_ssh_access]
    
    # Initialize a ReAct (Reason + Act) agent [cite: 343]
    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
        verbose=True, # This lets us see the agent's internal "thoughts" in the terminal
        handle_parsing_errors=True
    )

    # Give the agent its final instructions based on the Alert and the SOP
    prompt = f"""
    You are an autonomous Cloud Security Agent. 
    An alert occurred: {alert_desc}. 
    The affected resource is: {sg_id}.
    
    Here is the company SOP for fixing this:
    {sop_context}
    
    Your task: Use your available tools to fix the affected resource exactly as the SOP instructs.
    """

    print("\n🧠 Handing control over to the LangChain Agent...\n")
    agent.run(prompt)

if __name__ == "__main__":
    run_autonomous_agent()