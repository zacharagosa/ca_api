import looker_sdk
import os

print("Initializing Looker SDK...")
try:
    sdk = looker_sdk.init40()
    print("Looker SDK initialized successfully")
except Exception as e:
    print(f"Error initializing Looker SDK: {e}")
    import traceback
    traceback.print_exc()
