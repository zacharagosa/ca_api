from agent import app, PROJECT_ID, LOCATION

# Vertex AI is initialized in agent.py

def main():
    print("Starting chat with Data Agent. Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        try:
            # AdkApp uses stream_query and requires user_id
            response_stream = app.stream_query(message=user_input, user_id="local_user")
            print("Agent: ", end="", flush=True)
            for chunk in response_stream:
                if isinstance(chunk, dict) and "content" in chunk:
                    content = chunk["content"]
                    if "parts" in content:
                        for part in content["parts"]:
                            if "text" in part:
                                print(part["text"], end="", flush=True)
            print() # Newline at the end
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
