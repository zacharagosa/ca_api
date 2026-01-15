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

### Granting User Access (Complete Checklist)

There are **three access layers** that may need to be configured for a new user:

#### Step 1: Google OAuth Test Users (Required if OAuth is in "Testing" mode)

If your OAuth consent screen is in "Testing" mode, you must add users to the test users list:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Scroll to **Test users** section
4. Click **ADD USERS** and add the user's email
5. Save

> **Note**: If you publish the app to "In production" mode, this step is not needed (but unverified apps will show a warning screen to users).

#### Step 2: Cloud Run Access (Currently Public)

The service is currently configured with `allUsers` access, so this step is **not required**. However, if you want to restrict access to specific users:

```bash
# Remove public access first
gcloud run services remove-iam-policy-binding gaming-analytics \
  --project aragosalooker \
  --region us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"

# Then grant individual users
./scripts/grant_access.sh user@example.com
```

#### Step 3: Looker Permissions (If Applicable)

Users need appropriate Looker permissions to view data. This is managed in your Looker Admin panel:
- Users need access to the `gaming` model and `events` explore
- Grant via Looker Groups or individual user permissions

### Access Management Scripts

| Script | Description |
|--------|-------------|
| `./scripts/grant_access.sh email` | Grant Cloud Run access |
| `./scripts/revoke_access.sh email` | Remove Cloud Run access |
| `./scripts/list_access.sh` | List all authorized users |

### For End Users

1. **Have admin complete the checklist above** for your email
2. **Sign into Chrome** with your authorized Google account
3. **Navigate to the service URL**: https://gaming-analytics-wyjzl3wjfa-uc.a.run.app

### Troubleshooting Access Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Request submitted" screen | OAuth consent screen in Testing mode | Add user to OAuth test users (Step 1) |
| "403 Forbidden" | Cloud Run IAM blocking | Run `./scripts/grant_access.sh email` |
| App loads but no data | Looker permissions missing | Grant Looker access (Step 3) |
| "Sign-in error" popup | Invalid OAuth client config | Verify `VITE_GOOGLE_CLIENT_ID` |

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
