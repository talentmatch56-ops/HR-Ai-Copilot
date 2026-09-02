import os
import sys
import importlib.util

# Calculate base paths
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_app_dir = os.path.join(current_dir, "backend", "app")
mcp_server_dir = os.path.join(current_dir, "mcp-server")

for p in [backend_app_dir, mcp_server_dir, current_dir]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# Load the FastAPI app from backend/app/main.py directly
app_file = os.path.join(backend_app_dir, "main.py")
spec = importlib.util.spec_from_file_location("backend_main", app_file)
backend_main = importlib.util.module_from_spec(spec)
sys.modules["backend_main"] = backend_main
spec.loader.exec_module(backend_main)

app = backend_main.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
