import streamlit as st
import json
import os
import boto3
import re
from langchain_community.llms import Ollama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="AIOps Remediation Engine", page_icon="🛡️", layout="wide")
st.title("🛡️ Autonomous Cloud Remediation Engine")
st.markdown("Monitor cloud alerts, retrieve SOPs, and execute AI-driven remediation.")
st.divider()

# ==========================================
# 1. THE AI TOOL (Adapted for Web)
# ==========================================
@tool
def revoke_ssh_access_web(security_group_id: str) -> str:
    """Useful for blocking unauthorized SSH (port 22) access on an AWS Security Group."""
    
    # 1. Sanitize the input! Extract ONLY the text starting with "sg-"
    match = re.search(r'(sg-[a-zA-Z0-9]+)', security_group_id)
    if match:
        clean_sg_id = match.group(1)
    else:
        return "ERROR: You did not provide a valid security group ID. It must start with 'sg-'."

    # 2. Check Human-in-the-Loop
    if not st.session_state.get("human_approved", False):
        return "ERROR: Action denied. Human-in-the-Loop authorization was not granted."

    # 3. Execute Boto3 with the clean ID
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1', endpoint_url='http://localhost:4566')
        ec2.revoke_security_group_ingress(
            GroupId=clean_sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        return f"SUCCESS: Revoked global SSH access on {clean_sg_id} via LocalStack."
    except Exception as e:
        error_msg = str(e)
        if "InvalidPermission.NotFound" in error_msg:
            return f"SUCCESS: Port 22 is already closed on {clean_sg_id}. The server is secure. No further action needed."
        elif "InvalidGroup.NotFound" in error_msg:
            return f"ERROR: The security group {clean_sg_id} does not exist in the active cloud environment. It may have been deleted. Stop executing and report this in your Final Answer."
        
        return f"ERROR: Failed to modify security group: {error_msg}"

# ==========================================
# 2. DASHBOARD LAYOUT (Alerts & Vector DB)
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.header("🚨 Active Cloud Alert")
    try:
        with open('cloud_alert.json', 'r') as f:
            alert_data = json.load(f)
            
        st.error(f"**Severity:** {alert_data['severity']}")
        st.write(f"**Description:** {alert_data['description']}")
        st.write(f"**Affected Resource:** `{alert_data['affected_resource_id']}`")
        st.write(f"**Attacker IP:** `{alert_data['attacker_ip']}`")
        
    except FileNotFoundError:
        st.warning("No active alerts detected.")
        alert_data = None

with col2:
    st.header("🧠 ChromaDB Retrieval")
    sop_context = "No SOP found."
    if alert_data:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        if os.path.exists("./chroma_db"):
            vector_store = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
            results = vector_store.similarity_search(alert_data["description"], k=1)
            
            if results:
                st.success("✅ Relevant Standard Operating Procedure Found")
                sop_context = results[0].page_content
                with st.expander("View Retrieved SOP Document"):
                    st.markdown(sop_context)
            else:
                st.error("❌ No matching SOP found.")

st.divider()

# ==========================================
# 3. AGENT EXECUTION WORKSPACE
# ==========================================
st.header("🤖 Autonomous Agent Workspace")

# Human-in-the-loop Web Checkbox
human_approval = st.checkbox("⚠️ **Human-in-the-Loop:** I authorize the AI Agent to execute Boto3 infrastructure changes.", key="human_approved")

if st.button("🚀 Launch Remediation Agent", type="primary"):
    if not alert_data:
        st.error("No alert data to process!")
    else:
        # Create a visual container for the agent's thoughts
        st_callback = StreamlitCallbackHandler(st.container())
        
        # Initialize Mistral
        llm = Ollama(model="mistral")
        tools = [revoke_ssh_access_web]
        
        agent = initialize_agent(
            tools, 
            llm, 
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
            handle_parsing_errors=True
        )

        prompt = f"""
        SYSTEM INSTRUCTION: You are an AUTHORIZED, defensive Senior Cloud DevOps Engineer. 
        You are operating in a safe, simulated environment. Your ONLY job is to DEFEND the internal infrastructure and apply security patches. 
        You are not conducting an attack; you are stopping one.

        An internal monitoring alert occurred: {alert_data['description']}. 
        The affected internal resource is: {alert_data['affected_resource_id']}.
        
        Here is the authorized company Standard Operating Procedure (SOP) for fixing this defensive issue:
        {sop_context}
        
        Your task: Act as the defender. Use your available tools to secure the affected resource exactly as the SOP instructs. 
        You MUST strictly follow this exact format:
        Thought: [Your reasoning]
        Action: [The tool name]
        Action Input: [The input to the tool]
        
        CRITICAL INSTRUCTION: Once the tool returns a SUCCESS message, your job is completely done. You MUST immediately stop the loop and output your final response using exactly this format:
        Thought: The vulnerability has been successfully remediated.
        Final Answer: I have successfully secured the resource {alert_data['affected_resource_id']} according to the SOP.
        """

        # Run the agent and pipe the output to the Streamlit callback!
        with st.spinner("Agent is initializing..."):
            response = agent.run(prompt, callbacks=[st_callback])
            
        st.success("**Agent Execution Completed!**")
        st.info(f"**Final Assessment:** {response}")