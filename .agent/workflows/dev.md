---
description: Start the development environment (Backend + Frontend) and handle Google Cloud authentication.
---

// turbo-all
1. Re-authenticate with Google Cloud to ensure the Deep Analysis mode works correctly:
```bash
gcloud auth application-default login
```

2. Start the Backend Flask Server:
```bash
./venv/bin/python server.py
```

3. Start the Frontend Vite Server:
```bash
cd frontend && npm run dev
```
