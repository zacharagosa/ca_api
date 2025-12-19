/**
 * get_insights.js
 *
 * Simplified version.
 */
require('dotenv').config();
const { DataChatServiceClient } = require('@google-cloud/geminidataanalytics').v1alpha;

async function getInsights(question) {
    const client = new DataChatServiceClient();

    const projectId = process.env.PROJECT_ID || 'aragosalooker';
    const location = process.env.LOCATION || 'us-central1';

    // Construct the request object using simple JSON
    const request = {
        parent: `projects/${projectId}/locations/global`,
        inlineContext: {
            systemInstruction: { parts: [{ text: "You are a data analyst. Output SQL and Data." }] },
            datasourceReferences: {
                looker: {
                    exploreReferences: [{
                        lookerInstanceUri: process.env.LOOKER_INSTANCE_URI,
                        lookmlModel: process.env.LOOKML_MODEL || 'gaming',
                        explore: process.env.EXPLORE || 'events',
                    }],
                    credentials: {
                        oauth: {
                            secret: {
                                clientId: process.env.LOOKER_CLIENT_ID,
                                clientSecret: process.env.LOOKER_CLIENT_SECRET,
                            },
                        },
                    },
                },
            },
        },
        messages: [{ userMessage: { text: question } }],
    };

    try {
        // 1. Make the call
        const stream = client.chat(request);

        // 2. Simple accumulator
        let finalText = "";
        let finalData = null;

        // 3. Just loop and grab what we need, ignoring the "chunk" concept conceptually
        for await (const item of stream) {
            if (item.systemMessage?.text) {
                finalText += item.systemMessage.text;
            }
            if (item.systemMessage?.data) {
                // Usually the data comes in one big block or the last block has the full result
                // We'll just take the last 'data' block we see as the result
                finalData = item.systemMessage.data;
            }
        }

        return {
            text: finalText,
            data: finalData
        };

    } catch (err) {
        console.error("Error:", err.message);
        return { error: err.message };
    }
}

// Allow running directly
if (require.main === module) {
    const q = process.argv[2] || "Count events by date for the last 7 days";
    getInsights(q).then(res => console.log(JSON.stringify(res, null, 2)));
}

module.exports = { getInsights };
