import os
print("Importing agent...")
try:
    import agent
    print("Agent imported successfully")
except Exception as e:
    print(f"Error importing agent: {e}")
    import traceback
    traceback.print_exc()

print("Importing server...")
try:
    import server
    print("Server imported successfully")
except Exception as e:
    print(f"Error importing server: {e}")
    import traceback
    traceback.print_exc()
