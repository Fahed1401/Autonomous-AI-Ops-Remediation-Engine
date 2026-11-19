"""Read-only RAG/fallback smoke check, replacing the legacy script."""
import json
from aiops.integrations import retrieve_runbook


def main():
    result = retrieve_runbook("EC2 security group public SSH TCP 22 0.0.0.0/0")
    print(json.dumps({"title": result["title"], "source": result["source"],
                      "mode": result["mode"], "excerpt": result["body"][:450]}, indent=2))
    if not result["body"]:
        raise SystemExit("No runbook available. See company_docs/SOP_SentinelOps_Demo.md")


if __name__ == "__main__":
    main()
