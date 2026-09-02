import os
import jwt
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import settings
from services.agent_service import agent_service
from services.mcp_client import mcp_client
from db.session import init_db

app = FastAPI(title="HR AI Copilot Backend", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()

# Enable CORS for frontend communication across all devices & Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https?://.*",
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
DOCS_DIR = os.path.join(STATIC_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

# Mount static directory for serving generated PDFs
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Helper to verify JWT token and retrieve user metadata
def get_current_user(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Pydantic input models
class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    token: str

class ToolExecutionRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any]
    token: str

@app.post("/auth/login")
def login(req: LoginRequest):
    """Log in locally with predefined roles for evaluation purposes."""
    email = req.email.strip().lower()
    
    # Assign roles dynamically based on email
    if "admin" in email:
        role = "Admin"
    elif "hr" in email:
        role = "HR"
    elif "manager" in email:
        role = "Manager"
    else:
        role = "Employee"
        
    token_data = {
        "sub": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    
    token = jwt.encode(token_data, settings.JWT_SECRET, algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": email,
            "role": role
        }
    }

@app.get("/auth/google")
def google_auth_login():
    """Trigger Google OAuth login redirect URL."""
    google_oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/userinfo.email%20https://www.googleapis.com/auth/userinfo.profile"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return {"url": google_oauth_url}

@app.get("/auth/callback")
async def google_auth_callback(code: str):
    """Handle Google OAuth callback, exchange code for tokens, and return JWT."""
    if settings.GOOGLE_CLIENT_ID == "mock-client-id":
        email = "oauth.user@company.com"
        role = "Admin"
    else:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                token_res = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": code,
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                        "grant_type": "authorization_code"
                    }
                )
                token_data = token_res.json()
                access_token = token_data.get("access_token")
                
                user_info = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                email = user_info.json().get("email", "oauth.user@company.com")
                role = "HR" if "hr" in email else "Employee"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to authenticate with Google: {str(e)}")

    token_payload = {
        "sub": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(token_payload, settings.JWT_SECRET, algorithm="HS256")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": email,
            "role": role
        }
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    """Handle HR AI Chat query and route through OpenAI and MCP tools."""
    user = get_current_user(req.token)
    response = await agent_service.handle_message(
        message=req.message,
        history=req.history,
        user_role=user["role"],
        user_email=user["sub"]
    )
    return response

from fastapi import BackgroundTasks

async def simulate_slack_telemetry(user: str, tool: str, arguments: dict):
    """Simulate outbound Slack/Teams webhook telemetry notifications."""
    import json
    # Print outbound webhook alerts to console / logs
    print(f"\n[SLACK TELEMETRY WEBHOOK] -> channel: #hr-alerts | text: User {user} executed tool {tool} with arguments {json.dumps(arguments)}\n")

@app.post("/mcp/execute")
async def execute_tool(req: ToolExecutionRequest, background_tasks: BackgroundTasks):
    """Allow direct manual invocation of an MCP tool (privileged) asynchronously."""
    user = get_current_user(req.token)
    if user["role"] not in ["Admin", "HR"] and req.tool in ["send_email", "update_sheet"]:
        raise HTTPException(status_code=403, detail="Permission Denied for tool execution.")
        
    # Queue heavy document tasks as non-blocking background threads
    if req.tool in ["send_email", "generate_salary_slip", "generate_offer_letter", "generate_extension_letter"]:
        background_tasks.add_task(mcp_client.execute_tool, req.tool, req.arguments)
        background_tasks.add_task(simulate_slack_telemetry, user["sub"], req.tool, req.arguments)
        return {"status": "success", "message": f"Tool '{req.tool}' execution shifted to background worker queue."}
        
    # Invalidate candidate list cache if sheet is updated
    if req.tool == "update_employee_status":
        from services.redis_cache import redis_cache
        redis_cache.delete("employees_all")
        
    result = await mcp_client.execute_tool(req.tool, req.arguments)
    return result

@app.get("/audit/logs")
def get_audit_logs(token: str):
    """Expose the real-time execution audit logs."""
    user = get_current_user(token)
    if user["role"] not in ["Admin", "HR"]:
        raise HTTPException(status_code=403, detail="Access denied to audit logs.")
    return agent_service.get_audit_logs()

@app.get("/employees")
async def list_employees(token: str, query: Optional[str] = None, sheet_id: Optional[str] = None, force_refresh: Optional[bool] = False):
    """Expose search/list of employees directly from sheets database."""
    user = get_current_user(token)
    from services.redis_cache import redis_cache
    cache_key = f"employees_all_{sheet_id or 'default'}"
    if query:
        cache_key = f"employees_search_{query.strip().lower()}_{sheet_id or 'default'}"

    # Skip cache entirely when force_refresh=true (Real-time Sync button)
    if not force_refresh:
        cached_data = redis_cache.get(cache_key)
        if cached_data is not None:
            return cached_data

    try:
        from server import sheets
        if query:
            res = sheets.search_employee(name=query, sheet_id=sheet_id)
        else:
            res = sheets.read_sheet("Master Recruitment Tracker 2026", sheet_id=sheet_id)

        # Refresh cache with latest data
        redis_cache.set(cache_key, res, expire_seconds=10)
        return res
    except Exception as e:
        return []

class PolicyUploadRequest(BaseModel):
    title: str
    content: str
    token: str

@app.post("/policies/upload")
async def upload_policy(req: PolicyUploadRequest):
    """Save custom handbook policies into RAG database memory."""
    user = get_current_user(req.token)
    if user["role"] not in ["Admin", "HR"]:
        raise HTTPException(status_code=403, detail="Only Admins/HR can upload policies.")
    from db.session import SessionLocal
    from db.models import PolicyDocument
    db = SessionLocal()
    try:
        new_doc = PolicyDocument(title=req.title, content=req.content)
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        return {"status": "success", "message": f"Policy '{req.title}' successfully indexed into RAG memory."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save policy: {str(e)}")
    finally:
        db.close()

class AutoRespondRequest(BaseModel):
    candidate_message: str
    token: str

@app.post("/auto-respond")
async def auto_respond(req: AutoRespondRequest):
    """Generate automatic reply draft to a candidate's policy question using RAG."""
    user = get_current_user(req.token)
    if user["role"] not in ["Admin", "HR"]:
        raise HTTPException(status_code=403, detail="Only Admins/HR can draft auto-responses.")
        
    from services.rag_service import rag_service
    docs = await rag_service.search(req.candidate_message, top_k=1)
    
    body_text = "We are currently reviewing our guidelines and will get back to you shortly."
    if docs:
        body_text = f"Regarding our policy on '{docs[0]['title']}':\n{docs[0]['content']}"

    draft_body = (
        f"Hi,\n\n"
        f"Thank you for contacting us.\n\n"
        f"Here is the information we found in our handbook:\n\n"
        f"{body_text}\n\n"
        f"Please let us know if you have additional questions.\n\n"
        f"Best regards,\n"
        f"HR Operations Team"
    )
    return {"subject": f"RE: Inquiry regarding company policy", "body": draft_body}

class RegisterSheetRequest(BaseModel):
    sheet_id: str
    token: str
    title: Optional[str] = None

@app.get("/sheets")
def list_registered_sheets(token: str):
    """List all registered custom Google Sheets."""
    user = get_current_user(token)
    from db.session import SessionLocal
    from db.models import RegisteredSheet
    db = SessionLocal()
    try:
        sheets_list = db.query(RegisteredSheet).all()
        return [s.to_dict() for s in sheets_list]
    finally:
        db.close()

@app.post("/sheets/register")
async def register_sheet(req: RegisterSheetRequest):
    """Register a new Google Sheet ID to load in workspace."""
    user = get_current_user(req.token)
    if user["role"] not in ["Admin", "HR"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR can register custom sheets.")
    
    from db.session import SessionLocal
    from db.models import RegisteredSheet
    from server import sheets as sheet_helper
    
    title = req.title
    if not title:
        try:
            rows = sheet_helper.read_sheet("Master Recruitment Tracker 2026", sheet_id=req.sheet_id)
            if not rows:
                title = f"Sheet ({req.sheet_id[:8]}...)"
            else:
                title = f"Recruitment Tracker ({req.sheet_id[:8]})"
        except Exception:
            title = f"Custom Sheet ({req.sheet_id[:8]}...)"
            
    db = SessionLocal()
    try:
        existing = db.query(RegisteredSheet).filter(RegisteredSheet.sheet_id == req.sheet_id).first()
        if existing:
            return {"status": "success", "message": "Sheet already registered.", "sheet": existing.to_dict()}
            
        new_sheet = RegisteredSheet(sheet_id=req.sheet_id, title=title)
        db.add(new_sheet)
        db.commit()
        db.refresh(new_sheet)
        return {"status": "success", "message": "Sheet successfully registered!", "sheet": new_sheet.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register sheet: {str(e)}")
    finally:
        db.close()
