# Gaming Analytics Agent

This project is a sophisticated conversational analytics AI that enables users to query their gaming data using natural language. Built with **Google Cloud's Gemini 3 Pro**, **Vertex AI Reasoning Engines**, and **Looker**, it delivers real-time insights, interactive visualizations, and deep analytical reasoning.

![Agent Demo](assets/CA_demo.gif)

## Features

-   **Unified Analytics Agent**: A single, powerful agent that intelligently routes queries:
    -   **Simple Queries**: Instantly retrieves metrics and trends (e.g., "What is the DAU?", "Show revenue by country").
    -   **Deep Analysis**: Automatically triggers a multi-step reasoning plan for complex questions (e.g., "Compare iOS vs Android retention", "Why did revenue drop yesterday?"), breaking them down into sub-queries and synthesizing the results.
-   **Looker Integration**: dynamic SQL generation and execution against your LookML models.
-   **Interactive Visualizations**: Automatically requests and renders appropriate charts (Bar, Line, Pie) using Chart.js based on the data context.
-   **Live Thinking Process**: Exposes the agent's internal monologue ("THOUGHT: Analyzing request...", "THOUGHT: Querying Looker for daily active users..."), building trust and transparency.
-   **Structured Outputs**: Returns data in clean Markdown tables and rich JSON metadata for the frontend.
-   **Re-authentication**: Built-in flow to handle Google Cloud credential refreshment seamlessly.

## Architecture

-   **Backend**: Python (Flask) server (`server.py`) serving as the bridge between the frontend and the Vertex AI Reasoning Engine.
-   **AI Core**: `agent.py` defines the `UnifiedAnalyticsAgent` using the Google ADK (Agent Development Kit).
    -   **Model**: Gemini 3 Pro & Flash.
    -   **Tools**:
        -   `get_insights`: The primary tool for SQL generation and execution.
        -   `perform_deep_analysis`: An implementation of a planning agent loop for complex tasks.
        -   `VisualizatonAgent`: A specialized sub-agent for generating Chart.js configurations.
-   **Frontend**: A modern React (Vite) application (`frontend/`) providing the chat interface, real-time streaming (using `StreamWithContext`), and chart rendering.

## Setup & Configuration

### Prerequisites
-   Python 3.11+
-   Node.js 18+ & npm
-   Google Cloud SDK (`gcloud`) installed and authorized.
-   Access to a Google Cloud Project with Vertex AI enabled.
-   A Looker instance and API credentials.

### Installation

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd ca_api
    ```

2.  **Backend Setup**
    ```bash
    # Create and activate virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install Python dependencies
    pip install -r requirements.txt
    ```

3.  **Environment Variables**
    Create a `.env` file in the root directory with your credentials:
    ```env
    PROJECT_ID=your-google-cloud-project-id
    LOCATION=global
    LOOKER_CLIENT_ID=your_looker_client_id
    LOOKER_CLIENT_SECRET=your_looker_client_secret
    LOOKER_INSTANCE_URI=https://your-instance.looker.com
    LOOKML_MODEL=gaming
    EXPLORE=events
    ```

4.  **Frontend Setup**
    ```bash
    cd frontend
    npm install
    ```

## Running the Application

1.  **Start the Backend Server**
    In the root directory:
    ```bash
    source venv/bin/activate
    python3 server.py
    ```
    *The server runs on `http://0.0.0.0:8080`*

2.  **Start the Frontend**
    In a new terminal:
    ```bash
    cd frontend
    npm run dev
    ```
    *Open `http://localhost:5173` in your browser.*

## Usage

1.  Navigate to the local URL (http://localhost:5173).
2.  If prompted, follow the instructions to authenticate using `gcloud auth application-default login`.
3.  **Ask a Question**:
    -   *Simple*: "What was the total revenue last week?"
    -   *Complex*: "Analyze the performance difference between the US and UK markets for the past month."
4.  **Explore Results**:
    -   View the raw data in the generated Markdown table.
    -   Interact with the generated charts.
    -   Click "View Source Query" to open the exploration directly in Looker.

## Troubleshooting

-   **"Reauthentication required"**: Click the "Re-auth" button in the UI or run `gcloud auth application-default login` manually.
-   **Looker Errors**: Verify your `.env` credentials and ensure the `LOOKML_MODEL` and `EXPLORE` names match your Looker project.
