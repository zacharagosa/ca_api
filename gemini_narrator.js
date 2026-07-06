/**
 * Gemini Narrative Visualization
 * 
 * This custom visualization takes the data from a Looker query, formats it into a 
 * chronological event log, and sends it to the Gemini API to generate a narrative story.
 */

looker.plugins.visualizations.add({
  // Configuration options for the visualization
  options: {
    backendUrl: {
      type: "string",
      label: "Backend Server URL",
      display: "text",
      default: "http://localhost:8080",
      placeholder: "e.g., https://your-backend-api.com",
      section: "Configuration"
    },
    backendToken: {
      type: "string",
      label: "Backend Auth Token",
      display: "text",
      placeholder: "Optional: Secret token to authenticate with the backend",
      section: "Configuration"
    },
    promptContext: {
      type: "string",
      label: "Context / Persona",
      display: "text",
      default: "You are the Chronarch, an ancient observer of the Great Loom. Narrate this 'Void Weaver' session. Interpret 'Silk' as a mystical resource, 'Stitches' as building energy, and 'Knots' as finishing moves. Describe the Loom-Walker's journey through nodes like a grand tapestry being woven.",
      section: "Configuration"
    },
    modelName: {
      type: "string",
      label: "Model Name",
      display: "text",
      default: "gemini-3.5-flash",
      placeholder: "e.g., gemini-3.5-flash, gemini-1.5-flash",
      section: "Configuration"
    }
  },

  // Set up the initial state of the visualization
  create: function (element, config) {
    element.innerHTML = `
      <style>
        .gemini-narrative-container {
          font-family: 'Open Sans', sans-serif;
          padding: 24px;
          height: 100%;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          background-color: #f8f9fa;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }
        .title {
          font-size: 20px;
          font-weight: 700;
          color: #202124;
        }
        .generate-btn {
          background-color: #1a73e8;
          color: white;
          border: none;
          padding: 10px 24px;
          border-radius: 8px;
          font-size: 14px;
          cursor: pointer;
          font-weight: 600;
          box-shadow: 0 1px 3px rgba(0,0,0,0.12);
          transition: all 0.2s;
        }
        .generate-btn:hover {
          background-color: #1557b0;
          box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        }
        .generate-btn:disabled {
          background-color: #dadce0;
          color: #80868b;
          cursor: not-allowed;
          box-shadow: none;
        }
        
        /* Dashboard Layout */
        .dashboard-grid {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        
        /* Summary Card */
        .card {
          background: white;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.05);
          border: 1px solid #e0e0e0;
        }
        .card-title {
          font-size: 16px;
          font-weight: 600;
          color: #5f6368;
          margin-bottom: 16px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .summary-text {
          font-size: 18px;
          line-height: 1.6;
          color: #202124;
        }

        /* Metrics Grid */
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
        }
        .metric-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          border: 1px solid #e0e0e0;
          text-align: center;
        }
        .metric-value {
          font-size: 28px;
          font-weight: 700;
          color: #1a73e8;
          margin-bottom: 4px;
        }
        .metric-label {
          font-size: 14px;
          color: #5f6368;
          font-weight: 500;
        }

        /* Timeline / Narrative */
        .timeline-content {
          font-size: 16px;
          line-height: 1.7;
          color: #3c4043;
        }
        .timeline-content h3 {
          color: #202124;
          font-size: 18px;
          margin-top: 24px;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 2px solid #e8f0fe;
        }
        .timeline-content ul {
          padding-left: 20px;
          margin-bottom: 16px;
        }
        .timeline-content li {
          margin-bottom: 8px;
        }
        .timeline-content strong {
          color: #1a73e8;
        }

        .status-msg {
          text-align: center;
          color: #5f6368;
          font-style: italic;
          padding: 20px;
        }
        .error-msg {
          color: #d93025;
          background: #fce8e6;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid #f1c2c0;
        }
      </style>
      
      <div class="gemini-narrative-container">
        <div class="header">
          <div class="title">✨ Gemini Storyteller</div>
          <button id="generateBtn" class="generate-btn">Analyze Session</button>
        </div>

        <div id="statusMsg" class="status-msg" style="display:none;">
          Analyzing event data... extracting insights... writing story...
        </div>

        <div id="dashboardContent" class="dashboard-grid" style="display:none;">
          <!-- Summary Section -->
          <div class="card">
            <div class="card-title">Session Overview</div>
            <div id="summaryText" class="summary-text"></div>
          </div>

          <!-- Metrics Section -->
          <div id="metricsGrid" class="metrics-grid">
            <!-- Metrics injected here -->
          </div>

          <!-- Timeline Section -->
          <div class="card">
            <div class="card-title">Chronological Narrative</div>
            <div id="timelineText" class="timeline-content"></div>
          </div>
        </div>
        
        <div id="initialMsg" class="status-msg">
          Ready to analyze. Click the button above to start.
        </div>
      </div>
    `;

    this._generateBtn = element.querySelector("#generateBtn");
    this._statusMsg = element.querySelector("#statusMsg");
    this._dashboardContent = element.querySelector("#dashboardContent");
    this._summaryText = element.querySelector("#summaryText");
    this._metricsGrid = element.querySelector("#metricsGrid");
    this._timelineText = element.querySelector("#timelineText");
    this._initialMsg = element.querySelector("#initialMsg");

    // Bind click event
    this._generateBtn.addEventListener("click", () => {
      this.generateNarrative();
    });
  },

  // Render the visualization in response to data or config changes
  updateAsync: function (data, element, config, queryResponse, details, done) {
    this.clearErrors();
    this._data = data;
    this._config = config;
    this._queryResponse = queryResponse;

    // Check if Backend URL is present
    if (!config.backendUrl) {
      this.addError({
        title: "Missing Backend Server URL",
        message: "Please enter your backend server URL in the visualization settings."
      });
      this._generateBtn.disabled = true;
    } else {
      this._generateBtn.disabled = false;
    }

    done();
  },

  // Core logic to generate narrative
  generateNarrative: async function () {
    if (!this._data || this._data.length === 0) return;

    const backendUrl = this._config.backendUrl || "http://localhost:8080";
    const backendToken = this._config.backendToken;
    const context = this._config.promptContext || "You are a master storyteller narrating a gameplay session based on raw event logs.";

    // 1. Prepare Data Payload
    const maxRows = 500;
    const headers = this._queryResponse.fields.dimensions.map(d => d.label_short || d.label).join(", ");

    let csvContent = headers + "\n";
    this._data.slice(0, maxRows).forEach(row => {
      const rowText = this._queryResponse.fields.dimensions.map(field => {
        return LookerCharts.Utils.textForCell(row[field.name]);
      }).join(", ");
      csvContent += rowText + "\n";
    });

    // 2. Construct Prompt for JSON output
    const prompt = `
      ${context}
      
      Analyze the following log of game events.
      Provide the output strictly as a JSON object. Do not include Markdown formatting characters like \`\`\`json or \`\`\`.
      
      The JSON object must have this structure:
      {
        "overview": "A concise paragraph summarizing the player's overall experience, goals, and playstyle during this session.",
        "metrics": [
          {"label": "Metric Name (e.g., Total Duration)", "value": "Value"},
          {"label": "Metric Name (e.g., Encounter Intensity)", "value": "Value"},
          {"label": "Metric Name (e.g., Primary Weapon)", "value": "Value"},
          {"label": "Metric Name (e.g., Key Struggle)", "value": "Value"}
        ],
        "timeline": "A rich markdown string describing the events chronologically. Use bold (**text**) for emphasis and headers (###) for time blocks or scenes."
      }
      
      DATA LOG:
      ${csvContent}
    `;

    // 3. UI Updates
    this._generateBtn.disabled = true;
    this._statusMsg.style.display = "block";
    this._initialMsg.style.display = "none";
    this._dashboardContent.style.display = "none";

    try {
      // 4. Call Secure Backend API
      const modelName = this._config.modelName || "gemini-3.5-flash";
      const headersMap = {
        "Content-Type": "application/json"
      };
      if (backendToken) {
        headersMap["Authorization"] = `Bearer ${backendToken}`;
      }
      
      // Ensure backendUrl doesn't have trailing slash
      const cleanBackendUrl = backendUrl.replace(/\/$/, "");
      const response = await fetch(`${cleanBackendUrl}/api/generate-narrative`, {
        method: "POST",
        headers: headersMap,
        body: JSON.stringify({
          prompt: prompt,
          model_name: modelName
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      // 5. Parse and Display Result
      if (result.text) {
        let rawText = result.text;

        // Cleanup markdown code blocks if Gemini ignores instruction
        rawText = rawText.replace(/```json/g, '').replace(/```/g, '').trim();

        const data = JSON.parse(rawText);

        // Render Summary
        this._summaryText.innerText = data.overview || "No summary provided.";

        // Render Metrics
        this._metricsGrid.innerHTML = "";
        if (data.metrics && Array.isArray(data.metrics)) {
          data.metrics.forEach(metric => {
            const div = document.createElement("div");
            div.className = "metric-card";
            div.innerHTML = `
              <div class="metric-value">${metric.value}</div>
              <div class="metric-label">${metric.label}</div>
            `;
            this._metricsGrid.appendChild(div);
          });
        }

        // Render Timeline (Marked.js is ideal, but simple replacement works for basic bold/headers)
        let timelineHtml = data.timeline || "No timeline provided.";
        timelineHtml = timelineHtml
          .replace(/### (.*?)\n/g, '<h3>$1</h3>')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br>');

        this._timelineText.innerHTML = timelineHtml;

        this._dashboardContent.style.display = "flex";
      } else {
        this._initialMsg.innerText = "No narrative generated. Please check your backend connection.";
        this._initialMsg.style.display = "block";
      }

    } catch (error) {
      console.error("Narrative Generation Error:", error);
      this._initialMsg.innerHTML = `<span class="error-msg">Error: ${error.message}. Check console for details.</span>`;
      this._initialMsg.style.display = "block";
    } finally {
      this._generateBtn.disabled = false;
      this._statusMsg.style.display = "none";
    }
  }
});
