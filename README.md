# Gaming Analytics Agent

A conversational analytics AI that enables users to query gaming data using natural language. Built with **Google Cloud's Gemini 3**, **Vertex AI**, and **Looker**.

![Agent Demo](assets/CA_demo.gif)

## Features

- **Unified Analytics Agent**: Intelligently routes queries between fast lookups and deep analysis
- **Looker Integration**: Dynamic SQL generation against LookML models
- **Interactive Visualizations**: Auto-generated charts (Bar, Line, Pie) using Chart.js
- **Live Thinking Process**: Transparent agent reasoning ("Analyzing...", "Querying Looker...")
- **Chat History**: Persistent conversations with full chart/table rendering

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Google Cloud SDK (`gcloud`)
- Access to a GCP Project with Vertex AI enabled
- Looker instance with API credentials

### Local Development

1. **Clone & Setup Backend**
   ```bash
   git clone <repo-url>
   cd ca_api
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create `.env` in the root directory:
   ```env
   PROJECT_ID=your-gcp-project-id
   LOCATION=global
   DATASET_NAME=events
   
   # Looker credentials
   LOOKER_CLIENT_ID=your_looker_client_id
   LOOKER_CLIENT_SECRET=your_looker_client_secret
   LOOKER_INSTANCE_URI=https://your-instance.looker.app
   LOOKML_MODEL=gaming
   EXPLORE=events
   ```

3. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Run Locally**
   ```bash
   # Terminal 1: Backend
   source venv/bin/activate
   python server.py
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```
   Open http://localhost:5173

---

## Cloud Deployment (Google Cloud Run)

Deploy the application to Google Cloud Run with IAM-based access control.

### Deploy

```bash
# Ensure .env is configured with your credentials
./deploy_cloud_run.sh
```

This will:
1. Build the React frontend
2. Deploy to Cloud Run with IAM authentication
3. Output the service URL

### Access Management

The deployed service requires Google IAM authentication. Only users explicitly granted access can use the application.

#### Grant Access to a User
```bash
./scripts/grant_access.sh user@example.com
```

#### Revoke Access
```bash
./scripts/revoke_access.sh user@example.com
```

#### List All Users with Access
```bash
./scripts/list_access.sh
```

#### Grant Access to a Google Group
To grant access to multiple users at once, create a Google Group and grant access to the group:
```bash
gcloud run services add-iam-policy-binding gaming-analytics \
  --project YOUR_PROJECT_ID \
  --region us-central1 \
  --member="group:analytics-users@your-domain.com" \
  --role="roles/run.invoker"
```

### For End Users

Once granted access, users can access the application by:

1. **Sign into Chrome** with their authorized Google account
2. **Navigate to the service URL** (provided after deployment)
3. The application will automatically authenticate using their Google identity

> **Note**: If users see a "403 Forbidden" error, verify they have been granted access using `./scripts/list_access.sh`

---

## Architecture

- **Backend**: Python Flask server (`server.py`)
- **AI Core**: `agent.py` with Gemini 3 Pro/Flash
  - `get_insights`: SQL generation via Conversational Analytics API
  - `perform_deep_analysis`: Multi-step reasoning for complex queries
- **Frontend**: React/Vite with Chart.js visualizations

## Dataset Configuration

Dataset-specific settings are stored in `datasets/`. To add a new dataset:

1. Create `datasets/your_dataset.yaml` with Looker connection details
2. Set `DATASET_NAME=your_dataset` in `.env`
3. Restart the server

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "403 Forbidden" on Cloud Run | User needs access - run `./scripts/grant_access.sh email` |
| "Reauthentication required" | Run `gcloud auth application-default login` |
| Looker errors | Verify `.env` credentials match your Looker instance |
| Charts not rendering | Check browser console for Chart.js errors |

## License

Internal use only.
