# Source review and remediation ledger

**Reviewed public files:** `app.py`, `agent_execution.py`, `reasoning_engine.py`, `ingest_sops.py`, `master_setup.py`, `test_retrieval.py`, `requirements.txt`, README. Review date: 2026-11-19.

This audit is based on the publicly visible GitHub source. The original repository could not be cloned to this container due to network restrictions; the supplied files are a clean replacement, not a checked-in patch to the original commit. Dependency installation, actual model inference, and an end-to-end LocalStack run were not possible in this review runtime. Syntax, pure unit tests, and local HTTP/GUI smoke tests can be run on the replacement.

| Source finding | Why it matters | Upgrade |
|---|---|---|
| `app.py`: session checkbox `human_approved` used by an LLM-callable Boto3 tool | Consent is not tied to a specific plan, target, or single execution | Server creates exact plan IDs; approval requires exact phrase and issues one-use token valid for 120s |
| `app.py`: regex searches for `sg-*` substring | Accepts contaminated identifiers | Full-pattern validation for 8 or 17 hex chars |
| `app.py`: `InvalidPermission.NotFound` is rendered as a successful outcome | Errors can hide stale or mismatched state | Verification reads current rules; exceptions never count as success |
| `agent_execution.py`: CLI `input()` in a tool called by a generative agent | Blocks UI and gives unbounded prompt-to-tool authority | Direct tool invocation removed; deterministic allowlisted operation |
| `reasoning_engine.py`: uses `llama3` whereas dashboard uses `mistral` | Confusing local model contract; runtime errors when model missing | Single optional `AIOPS_OLLAMA_MODEL`; deterministic fallback |
| Legacy `initialize_agent`, `Ollama`, `Chroma` imports from older LangChain paths | Breaks with newer major versions | Optional current libraries isolated; no AI imports at startup |
| RAG setup during dashboard reruns, with no source clarity | Resource cost and potentially missing embeddings | Retrieval happens only during plan analysis; explicit fallback provenance |
| `master_setup.py`: intentionally creates a public SSH ingress rule | Dangerous if endpoint were misconfigured | LocalStack adapter pins credentials and endpoint to loopback |
| `test_retrieval.py`: message refers to nonexistent `generate_alert.py` | Incorrect setup guidance | `master_setup.py` documented; new regression tests |
| No distinct production/dev safety posture, weak error isolation, sparse audit | Low confidence for portfolio demo | Local-only server, clear simulation mode, CSV audit, health, tested API |

## Residual limitations

This implementation demonstrates security-oriented design but is **not production-ready**. In particular, there is no authentication, persisted approvals, distributed idempotency, durable audit data, cloud IAM policy enforcement, incident telemetry, independent threat model, or production vulnerability assessment. Never deploy this API publicly without those controls.
