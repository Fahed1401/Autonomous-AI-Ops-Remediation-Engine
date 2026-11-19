"""Legacy direct agent execution is deliberately disabled for safety.

The original ReAct-based tool could mutate a resource based on session-level
approval. Use the gated web workflow rather than prompt-directed Boto3 calls.
"""


def main():
    raise SystemExit("Direct autonomous cloud mutation is disabled. Run `python3 api_server.py`, review a plan, explicitly approve it, and execute through the verified playbook.")


if __name__ == "__main__":
    main()
