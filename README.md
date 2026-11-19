# Autonomous AIOps Remediation Engine: A RAG-Driven Cloud Security Agent

An autonomous, locally hosted cloud security remediation engine that leverages **Large Language Models (LLMs)**, **Retrieval-Augmented Generation (RAG)**, and the **ReAct (Reason + Act)** prompting framework to detect, triage, and resolve cloud infrastructure vulnerabilities—safeguarded by a mandatory **Human-in-the-Loop (HITL)** interface.

---

## Overview

Modern Security Operations Centers (SOCs) suffer from severe alert fatigue and high Mean Time to Resolution (MTTR). Static automation scripts (such as rigid AWS Lambda functions) frequently fail when encountering environmental drift or unexpected API exceptions. 

This project implements a closed-loop, self-healing DevSecOps pipeline running entirely offline for maximum data privacy:
1. **Cloud Simulation (`LocalStack`):** Emulates AWS VPC and EC2 Security Group environments locally via Docker.
2. **Knowledge Grounding (`ChromaDB` + `HuggingFace`):** Embeds enterprise Standard Operating Procedures (SOPs) into a vector store and retrieves exact remediation protocols via Cosine Similarity.
3. **Cognitive Reasoning (`Mistral 7B` via `Ollama` + `LangChain`):** Synthesizes incoming JSON alerts with retrieved SOPs using a `Thought -> Action -> Observation` loop.
4. **Hardened Execution (`Boto3` + `Regex`):** Sanitizes LLM outputs using regular expressions before invoking deterministic AWS SDK calls.
5. **Governance (`Streamlit` HITL):** Halts execution and requires explicit human authorization prior to committing state-altering infrastructure changes.

---

## Project Structure

```text
Autonomous-AI-Ops-Remediation-Engine/
├── company_docs/
│   └── SOP_Security_Incident_Response.md   # Enterprise compliance & remediation runbooks
├── master_setup.py                         # Provisions vulnerable AWS VPC/SG in LocalStack & generates alert
├── ingest_sops.py                          # Chunks SOPs and builds the ChromaDB vector store
├── app.py                                  # Streamlit dashboard, LangChain ReAct agent & HITL guardrail
├── requirements.txt                        # Python dependencies
└── README.md                               # Project documentation
```

---

## Prerequisites

Ensure the following tools are installed and running on your local machine before executing the project:
* **Python 3.9+**
* **Docker Desktop** (for running LocalStack)
* **LocalStack CLI** (`pip install localstack`)
* **Ollama** with the Mistral 7B model pulled:
  ```bash
  ollama pull mistral
  ```

---

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Fahed1401/Autonomous-AI-Ops-Remediation-Engine.git
   cd Autonomous-AI-Ops-Remediation-Engine
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv cloud-agent-env
   source cloud-agent-env/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure dummy AWS credentials for LocalStack:**
   ```bash
   aws configure
   # AWS Access Key ID: test
   # AWS Secret Access Key: test
   # Default region name: us-east-1
   # Default output format: json
   ```

---

## How to Run

1. **Start LocalStack in the background:**
   ```bash
   localstack start -d
   ```

2. **Ingest Enterprise SOPs into ChromaDB:**
   ```bash
   python ingest_sops.py
   ```

3. **Simulate a Vulnerability & Trigger an Alert:**
   *(Creates a Security Group with TCP Port 22 open to `0.0.0.0/0` and outputs `cloud_alert.json`)*
   ```bash
   python master_setup.py
   ```

4. **Launch the Streamlit AIOps Dashboard:**
   ```bash
   streamlit run app.py
   ```

5. **Authorize & Verify Remediation:**
   * In the browser (`http://localhost:8501`), review the alert and retrieved SOP.
   * Check the **Human-in-the-Loop Authorization** box and click **Launch Remediation Agent**.
   * Verify via AWS CLI that the ingress rule has been stripped (`"IpPermissions": []`):
     ```bash
     aws --endpoint-url=http://localhost:4566 ec2 describe-security-groups --region us-east-1
     ```

---

## Author

* **Fahed Ahmad** — B.Tech in Artificial Intelligence & Machine Learning, University School of Automation and Robotics (USAR), GGSIPU
* **Mentor:** Dr. Rahul Johri, Assistant Professor, USAR, GGSIPU