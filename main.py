import os
import sys
import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))
self_path = os.path.abspath(__file__)

# Candidate locations where backend main.py might be located
candidate_paths = [
    os.path.join(current_dir, "backend", "app", "main.py"),
    os.path.join(current_dir, "app", "main.py"),
    os.path.join(current_dir, "HR_Co-pilot", "backend", "app", "main.py"),
    os.path.join(current_dir, "HR-Co-Pilot", "backend", "app", "main.py"),
    os.path.join(current_dir, "hr-ai-copilot", "backend", "app", "main.py"),
]

app_file = None
for p in candidate_paths:
    if os.path.exists(p) and os.path.abspath(p) != self_path:
        app_file = p
        break

# If not in standard candidates, recursively search for backend/app/main.py
if not app_file:
    for root, dirs, files in os.walk(current_dir):
        if "main.py" in files:
            full_path = os.path.join(root, "main.py")
            if os.path.abspath(full_path) != self_path:
                app_file = full_path
                break

if not app_file or not os.path.exists(app_file):
    raise FileNotFoundError(f"Could not locate the FastAPI app main.py within {current_dir}")

app_dir = os.path.dirname(app_file)
repo_root = os.path.dirname(os.path.dirname(app_dir)) if "app" in app_dir else current_dir

# Find mcp-server directory
mcp_server_dir = os.path.join(repo_root, "mcp-server")
if not os.path.exists(mcp_server_dir):
    mcp_server_dir = os.path.join(current_dir, "mcp-server")

# Add all relevant paths to sys.path
for path in [app_dir, repo_root, mcp_server_dir, current_dir]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# Dynamically load the backend main module
spec = importlib.util.spec_from_file_location("backend_app_main", app_file)
backend_module = importlib.util.module_from_spec(spec)
sys.modules["backend_app_main"] = backend_module
spec.loader.exec_module(backend_module)

app = backend_module.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
