import socket

print("Creating socket...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Socket created. Binding to 127.0.0.1:8080...")
try:
    s.bind(('127.0.0.1', 8080))
    print("Bind successful")
except Exception as e:
    print(f"Bind failed: {e}")
finally:
    s.close()
