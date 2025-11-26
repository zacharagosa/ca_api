from agent import app, PROJECT_ID, LOCATION
import vertexai
import time

# Initialize Vertex AI for local execution
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket="gs://ca_api",
)

test_questions = [
    "What is the average session length for players on Android?",
    "Show me the lifetime revenue for users we acquired from Vungle.",
    "What is the D7 retention rate for users who installed the app from 'ironsource'?",
    "How many users are considered 'Whale' in terms of lifetime spend?",
    "What is the average number of days played by users?",
    "What is the total ad revenue generated from sessions in 'Lookerwood Farm' last month?",
    "How many sessions had a highest level reached greater than 10?",
    "What is the average number of events per session?",
    "How many sessions were the first session for a user?",
    "How many 'iap_purchase' events happened yesterday for 'Lookerwood Farm'?",
    "What was the total ad revenue from players in Germany last week?",
    "What is the total IAP revenue for the game 'Lookup Battle Royale' for users who installed from 'organic' sources?",
    "How many 'Level_Up' events occurred on iOS devices?",
    "What is the average revenue per user (ARPU) for users who triggered the 'Ad_Watched' event?",
    "Show me the trend of daily active users for the last 7 days.",
    "What is the total revenue by country for the last month?",
    "Break down the number of sessions by device type for the last week.",
    "Show me user acquisition by source over the last 30 days."
]

def run_tests():
    print(f"Running {len(test_questions)} test questions...\n")
    
    for i, question in enumerate(test_questions):
        print(f"--- Question {i+1}: {question} ---")
        try:
            # Use a unique user_id for each test to avoid context pollution if desired, 
            # or keep it same to test conversational ability. 
            # Here we use a new session for each question to test them independently.
            response_stream = app.stream_query(message=question, user_id=f"test_user_{i}")
            
            print("Agent: ", end="", flush=True)
            full_response = ""
            for chunk in response_stream:
                if isinstance(chunk, dict) and "content" in chunk:
                    content = chunk["content"]
                    if "parts" in content:
                        for part in content["parts"]:
                            if "text" in part:
                                text = part["text"]
                                print(text, end="", flush=True)
                                full_response += text
            print("\n")
            
        except Exception as e:
            print(f"\nError: {e}\n")
        
        # Small delay to avoid hitting rate limits too hard
        time.sleep(2)

if __name__ == "__main__":
    run_tests()
