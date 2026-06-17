import os
import sys
sys.path.insert(0, os.path.abspath('.'))

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

print("Starting server run...")
server.app.run(debug=False, use_reloader=False, host='127.0.0.1', port=8080)
