"""Read-only analyst CLI. Cloud changes must use the HITL web control plane."""
import argparse
import json

from aiops.service import OperationsService


def main():
    parser = argparse.ArgumentParser(description="Read-only incident analysis; never mutates infrastructure")
    parser.add_argument("--incident", help="Incident ID; omit to analyze the first actionable demo incident")
    parser.add_argument("--mode", choices=["demo", "localstack"], default="demo")
    args = parser.parse_args()
    svc = OperationsService(mode=args.mode)
    incidents = [i for i in svc.overview()["incidents"] if i["actionable"] and i["status"] != "Resolved"]
    if not incidents:
        parser.exit(1, "No actionable incidents were found.\n")
    plan = svc.analyze(args.incident or incidents[0]["id"])
    print(json.dumps({k: v for k, v in plan.items() if k not in {"runbook", "ai_summary"}}, indent=2))
    print("This command is read-only. To authorize and execute, launch python3 api_server.py.")


if __name__ == "__main__":
    main()
