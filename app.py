"""Convenience entrypoint for the upgraded independent web frontend.

Run with `python3 app.py`, not `streamlit run app.py`.
"""
from api_server import main

if __name__ == "__main__":
    main()
