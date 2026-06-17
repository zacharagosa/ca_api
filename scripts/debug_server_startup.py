import sys
import os
import traceback

sys.path.insert(0, os.path.abspath('.'))

try:
    import server
    print("Server imported successfully")
    print("Running app.run()...")
    server.app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)
except Exception as e:
    print(f"EXCEPTION CAUGHT: {e}")
    traceback.print_exc()
