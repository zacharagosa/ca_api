import requests
import json
import time

BASE_URL = "http://localhost:8080"
CHAT_URL = f"{BASE_URL}/chat"
HISTORY_URL = f"{BASE_URL}/api/history"

def test_history_lifecycle():
    print("--- Starting History Lifecycle Test ---")

    # 1. List initial history
    try:
        resp = requests.get(HISTORY_URL)
        initial_history = resp.json()
        print(f"Initial history count: {len(initial_history)}")
    except Exception as e:
        print(f"Failed to fetch initial history: {e}")
        return

    # 2. Create a new session via chat
    session_id = f"test_session_{int(time.time())}"
    payload = {
        "message": "Hello, this is a test message for history verification.",
        "session_id": session_id,
        "agent_type": "fast",
        "user_id": "test_user"
    }

    print(f"Sending chat message for session: {session_id}")
    try:
        # Stream response
        with requests.post(CHAT_URL, json=payload, stream=True) as r:
            for line in r.iter_lines():
                pass # Consume stream
        print("Chat message sent and response consumed.")
    except Exception as e:
        print(f"Failed to send chat message: {e}")
        return

    # Wait a moment for file I/O
    time.sleep(1)

    # 3. Verify it appears in history
    resp = requests.get(HISTORY_URL)
    new_history = resp.json()
    print(f"New history count: {len(new_history)}")
    
    found = False
    for item in new_history:
        if item['id'] == session_id:
            found = True
            print(f"Found new session in history: {item['title']} (ID: {item['id']})")
            break
    
    if not found:
        print("ERROR: New session not found in history list!")

    # 4. Verify conversation content
    print(f"Fetching content for session: {session_id}")
    resp = requests.get(f"{HISTORY_URL}/{session_id}")
    messages = resp.json()
    print(f"Messages in session: {len(messages)}")
    if len(messages) >= 2: # User + Agent
        print("SUCCESS: Session has user and agent messages.")
    else:
        print("WARNING: Session has fewer messages than expected.")

    # 5. Delete conversation
    print(f"Deleting session: {session_id}")
    requests.delete(f"{HISTORY_URL}/{session_id}")
    
    # 6. Verify deletion
    resp = requests.get(HISTORY_URL)
    final_history = resp.json()
    found_after_delete = any(item['id'] == session_id for item in final_history)
    
    if not found_after_delete:
        print("SUCCESS: Session successfully deleted.")
    else:
        print("ERROR: Session still exists after deletion!")

if __name__ == "__main__":
    test_history_lifecycle()
