# Cloud deployment verification

Checked on 3 October 2026 (IST).

- Live URL: https://commercegraph-utkarsh.streamlit.app/
- Source: https://github.com/utkarshagarwaldev/commercegraph
- Branch: main; Streamlit entry point: app.py.
- Runtime verified in cloud logs: Python 3.12.14 on Linux.
- Cloud dependencies installed successfully from requirements.txt using uv.
- The requirements manifest installs the dependency lock and local src-layout package.
- Hosted UI loaded successfully.
- Hosted graph: 58 nodes, 83 directed relationships.
- Hosted dataset audit: five matching marker nodes and five standalone graph occurrences.
- Prepared source copy: 120 offline tests passed; 14 explicitly live tests deselected.
- Exported source checked against the actual local API key: no matching credential.
- .env and .streamlit/secrets.toml are excluded from Git and the submission ZIP.
- .vercelignore excludes credentials and local artifacts from future CLI uploads.

Live Gemini questions still require the owner to configure GEMINI_API_KEY in
Streamlit Cloud encrypted Secrets. Hosted LLM execution has not yet been verified.

The original Streamlit entry point was not an ASGI/WSGI application, so its
Vercel deployment failed. The working Streamlit interface is hosted directly on
Streamlit Community Cloud. The original local project was preserved.
