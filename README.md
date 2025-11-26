# Gaming Analytics Agent

This project is a conversational analytics agent that allows users to query their gaming data using natural language. It leverages Google Cloud's Vertex AI and Looker to provide insights, data tables, and visualizations.

## Features

-   **Natural Language Queries**: Ask questions like "What is the total revenue for the last 30 days?" or "Show me a trend of daily active users".
-   **Real-time Streaming**: Responses are streamed to the frontend, providing immediate feedback.
-   **Thought Process**: The agent's internal "thoughts" (e.g., "Querying Looker...", "Processing results...") are displayed to the user.
-   **Data Visualization**: Automatically generates bar, line, and pie charts using Recharts based on the data returned.
-   **Markdown Tables**: Presents data in clean, readable Markdown tables.
-   **Auto-Test Mode**: A built-in feature to automatically cycle through a set of test questions to verify functionality.
-   **Re-authentication**: Includes a helper to refresh Google Cloud credentials if they expire.

## Architecture

-   **Backend**: Python (Flask) server (`server.py`) that orchestrates the agent.
-   **Agent**: Built with Google's Agent Development Kit (ADK) and Vertex AI (`agent.py`). It uses a multi-agent architecture:
    -   `RootAgent`: The main orchestrator that handles user interaction and formatting.
    -   `DataAgent`: Retrieves raw data from Looker using the `get_insights` tool.
    -   `VisualizationAgent`: Generates chart configurations from the data.
-   **Frontend**: React application (`frontend/`) that handles the chat interface, streaming, and rendering.

## Setup & Running

1.  **Prerequisites**:
    -   Python 3.11+
    -   Node.js & npm
    -   Google Cloud SDK (`gcloud`) installed and authenticated.

2.  **Backend**:
    ```bash
    # Install dependencies (if not already)
    pip install -r requirements.txt
    
    # Run the server
    python3 server.py
    ```
    The server runs on `http://127.0.0.1:5000`.

3.  **Frontend**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    The frontend runs on `http://localhost:5173`.

## Usage

1.  Open the frontend URL.
2.  Type a question in the chat box.
3.  View the "Thinking Process" as the agent works.
4.  See the results in text, table, and chart formats.
5.  Use the "Auto Test" button to verify all features.
6.  Use the "Re-auth" button if you encounter authentication errors.

## Troubleshooting

-   **Authentication Errors**: If you see `RefreshError`, click the "Re-auth" button or run `gcloud auth application-default login` in your terminal.
-   **Port Conflicts**: If the server fails to start, ensure port 5000 is free.
