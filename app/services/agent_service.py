import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI
from core.config import settings
from services.mcp_client import mcp_client

logger = logging.getLogger("agent_service")

def log_audit(user: str, tool: str, parameters: Dict[str, Any], response: Any, role: str = "User"):
    from db.session import SessionLocal
    from db.models import AuditLog
    db = SessionLocal()
    try:
        log_entry = AuditLog(
            user_email=user,
            user_role=role,
            tool_name=tool,
            parameters=json.dumps(parameters),
            response=json.dumps(response) if response else None
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit to DB: {e}")
    finally:
        db.close()

class AgentService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.is_mock = self.api_key == "mock-key-for-hr-ai-copilot" or not self.api_key
        if not self.is_mock:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.info("Initializing AgentService in offline demonstration mode.")

    def get_audit_logs(self) -> List[Dict[str, Any]]:
        from db.session import SessionLocal
        from db.models import AuditLog
        db = SessionLocal()
        try:
            logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
            return [log.to_dict() for log in logs]
        except Exception as e:
            logger.error(f"Failed to get audit logs from DB: {e}")
            return []
        finally:
            db.close()

    async def handle_message(self, message: str, history: List[Dict[str, str]], user_role: str, user_email: str) -> Dict[str, Any]:
        """Orchestrate conversation history, tool calls, and final response."""
        # 1. If we are running in Mock/Demo mode, use rule-based simulation
        if self.is_mock:
            return await self._simulate_agent_response(message, user_role, user_email)

        # Parse report helper details upfront
        msg_lower = message.lower()
        is_chart_query = any(k in msg_lower for k in ["chart", "graph", "bar chart", "visualize", "visualization"])
        is_report_query = is_chart_query or any(k in msg_lower for k in ["how many", "count", "added on", "added in", "report", "added", "list", "show me"])
        target_date_str = None
        target_months = []
        target_tech = None
        if is_report_query:
            import re
            # Check for quarter query filters
            if "last quarter" in msg_lower or "last quater" in msg_lower or "previous quarter" in msg_lower or "prev quarter" in msg_lower:
                target_months = ["Apr", "May", "Jun"]
                target_date_str = "Last Quarter (Q2 2026)"
            elif "quarter" in msg_lower or "quater" in msg_lower or "this quarter" in msg_lower or "this quater" in msg_lower:
                target_months = ["Jul", "Aug", "Sep"]
                target_date_str = "This Quarter (Q3 2026)"

            if not target_date_str:
                months_map = {
                    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
                }
                date_match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+([a-zA-Z]+)\s+(\d{4})", msg_lower)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month_name = date_match.group(2)[:3]
                    year = date_match.group(3)
                    if month_name in months_map:
                        target_date_str = f"{day}-{month_name.capitalize()}-{year}"
            
            tech_match = re.search(r"(?:for|in)\s+([a-zA-Z\s]+?)(?:\s+technology|\s+tech|$)", msg_lower)
            if tech_match:
                target_tech = tech_match.group(1).strip()
            else:
                for t in ["account", "python", "mern", "bde", "frontend", "ui/ux", "ba"]:
                    if t in msg_lower:
                        target_tech = t
                        break

        # 2. Real OpenAI implementation
        try:
            tools = mcp_client.get_openai_tool_schemas()
            
            # Setup base system prompt enforcing role limits
            system_prompt = (
                f"You are the HR AI Copilot assistant. The current date is {datetime.now().strftime('%Y-%m-%d')}.\n"
                f"You must strictly respect the user's role: {user_role}.\n"
                "- Admin & HR: Can execute all tools including sending emails and editing sheets.\n"
                "- Manager: Can view sheets and search clients, but cannot approve/send salary details or letters.\n"
                "- Employee: Can only view their own details and get leave balances.\n\n"
                "Whenever a user asks for employee or candidate details/profiles, you MUST format the response "
                "as a clean, structured Markdown table with columns: 'Field' and 'Detail'. Do NOT use bulleted lists for profiles.\n\n"
                "If a user asks to send an email, first generate the draft and tell the user they must approve it. "
                "Do NOT execute send_email without explicitly confirming that the user has seen the draft."
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": message})

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            steps = []
            if tool_calls:
                for tool_call in tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    # Security check: Check permissions
                    if user_role not in ["Admin", "HR"] and name in ["send_email", "update_sheet", "generate_salary_slip"]:
                        steps.append({
                            "tool": name,
                            "arguments": args,
                            "status": "denied",
                            "error": f"Role '{user_role}' does not have permissions to execute tool: {name}"
                        })
                        continue

                    # Executing tool
                    result = await mcp_client.execute_tool(name, args)
                    log_audit(user_email, name, args, result)
                    
                    steps.append({
                        "tool": name,
                        "arguments": args,
                        "status": "success" if result.get("status") != "error" else "error",
                        "response": result
                    })

                # Call LLM again with tool results
                tool_messages = messages.copy()
                tool_messages.append(response_message)
                for call, step in zip(tool_calls, steps):
                    if step["status"] == "success":
                        tool_messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": json.dumps(step["response"])
                        })
                
                final_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=tool_messages
                )
                
                response_text = final_response.choices[0].message.content
                
                # If query was a report query, append chart tag to live LLM output too
                if is_report_query:
                    try:
                        # Try to build chart from sheet response inside steps
                        sheet_step = next((s for s in steps if s["tool"] == "read_sheet"), None)
                        if sheet_step:
                            raw_resp = sheet_step.get("response")
                            all_emps = []
                            if isinstance(raw_resp, str):
                                try:
                                    all_emps = json.loads(raw_resp)
                                except Exception:
                                    pass
                            elif isinstance(raw_resp, list):
                                all_emps = raw_resp
                            elif isinstance(raw_resp, dict) and "data" in raw_resp:
                                all_emps = raw_resp["data"]
                            elif isinstance(raw_resp, dict) and "value" in raw_resp:
                                all_emps = raw_resp["value"]
                            # Use same filters as simulated mode
                            matched_candidates = []
                            for emp in all_emps:
                                emp_date = (emp.get("joining_date") or "").strip()
                                emp_tech = (emp.get("designation") or "").strip().lower()
                                date_ok = True
                                if target_date_str:
                                    day_clean = target_date_str.split('-')[0]
                                    month_clean = target_date_str.split('-')[1]
                                    date_ok = (day_clean in emp_date and month_clean.lower() in emp_date.lower())
                                
                                tech_ok = not target_tech or (target_tech.lower() in emp_tech or emp_tech in target_tech.lower())
                                if date_ok and tech_ok:
                                    matched_candidates.append(emp)
                            
                            if matched_candidates:
                                statuses = {}
                                for c in matched_candidates:
                                    st = c.get('status') or 'Unknown'
                                    statuses[st] = statuses.get(st, 0) + 1
                                import json
                                chart_payload = {
                                    "labels": list(statuses.keys()),
                                    "values": list(statuses.values()),
                                    "title": f"Candidate Statuses for {target_tech or 'All'} on {target_date_str or 'All'}"
                                }
                                response_text += f"\n\n[CHART_DATA: {json.dumps(chart_payload)}]"
                    except Exception as e:
                        logger.error(f"Failed to append chart to live LLM path: {e}")

                return {
                    "response": response_text,
                    "steps": steps
                }
            else:
                response_text = response_message.content
                if is_report_query:
                    # Fallback check if it didn't call read_sheet or returned directly
                    pass
                return {
                    "response": response_text,
                    "steps": []
                }
                
        except Exception as e:
            logger.error(f"Error in agent execution: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "steps": []
            }

    async def _simulate_agent_response(self, message: str, role: str, email: str) -> Dict[str, Any]:
        """Simulate LLM tool choices and logical flow for offline demonstration."""
        msg_lower = message.lower()
        words = msg_lower.split()
        steps = []
        response_text = ""

        # Check permissions
        is_privileged = role in ["Admin", "HR"]

        # 0. Policy / Knowledge Base Search (RAG)
        is_policy_query = (
            any(k in msg_lower for k in ["policy", "rules", "handbook", "guidelines", "operating hours", "remote work", "work from home", "how many days", "how to apply"]) or
            (any(k in msg_lower for k in ["maternity", "sick", "casual"]) and "leave" in msg_lower and not any(k in msg_lower for k in ["who", "anyone", "is on", "list", "active"]))
        )
        if is_policy_query:
            args = {"query": message}
            res = await mcp_client.execute_tool("search_knowledge_base", args)
            log_audit(email, "search_knowledge_base", args, res)
            steps.append({"tool": "search_knowledge_base", "arguments": args, "status": "success", "response": res})
            
            if isinstance(res, list) and len(res) > 0:
                doc = res[0]
                response_text = f"Here is what I found in our Policy Handbook:\n\n* **{doc.get('title')}**: {doc.get('content')}"
            else:
                response_text = "I couldn't find any policy matching your query in the handbook."
            return {"response": response_text, "steps": steps}

        # 0.5 Match report query (e.g., count candidates added on a specific date for a specific technology)
        is_chart_query = any(k in msg_lower for k in ["chart", "graph", "bar chart", "visualize", "visualization"])
        is_report_query = is_chart_query or any(k in msg_lower for k in ["how many", "count", "added on", "added in", "report", "added", "list", "show me"])
        if is_report_query:
            import re
            target_date_str = None
            target_months = []
            
            # Check for quarter query filters
            if "last quarter" in msg_lower or "last quater" in msg_lower or "previous quarter" in msg_lower or "prev quarter" in msg_lower:
                target_months = ["Apr", "May", "Jun"]
                target_date_str = "Last Quarter (Q2 2026)"
            elif "quarter" in msg_lower or "quater" in msg_lower or "this quarter" in msg_lower or "this quater" in msg_lower:
                target_months = ["Jul", "Aug", "Sep"]
                target_date_str = "This Quarter (Q3 2026)"

            if not target_date_str:
                months_map = {
                    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
                    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
                }
                # Look for 30th july 2026 or similar
                date_match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+([a-zA-Z]+)\s+(\d{4})", msg_lower)
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month_name = date_match.group(2)[:3]
                    year = date_match.group(3)
                    if month_name in months_map:
                        target_date_str = f"{day}-{month_name.capitalize()}-{year}"
            
            # Extract technology (e.g. account, developer, python, mern)
            target_tech = None
            tech_match = re.search(r"(?:for|in)\s+([a-zA-Z\s]+?)(?:\s+technology|\s+tech|$)", msg_lower)
            if tech_match:
                target_tech = tech_match.group(1).strip()
            else:
                for t in ["account", "python", "mern", "bde", "frontend", "ui/ux", "ba"]:
                    if t in msg_lower:
                        target_tech = t
                        break

            # Fetch all candidates using tool
            args = {"sheet_name": "Master Recruitment Tracker 2026"}
            res = await mcp_client.execute_tool("read_sheet", args)
            steps.append({"tool": "read_sheet", "arguments": args, "status": "success", "response": res})
            
            all_emps = []
            if isinstance(res, list):
                all_emps = res
            elif isinstance(res, dict) and "data" in res:
                all_emps = res["data"]
            elif isinstance(res, dict) and "value" in res:
                all_emps = res["value"]

            # Filter candidates
            matched_candidates = []
            for emp in all_emps:
                emp_date = (emp.get("joining_date") or "").strip()
                emp_tech = (emp.get("designation") or "").strip().lower()
                
                # Check date match
                date_ok = True
                if target_date_str:
                    if target_months:
                        # Match Q2 or Q3 months for year 2026 (or 2025/2026)
                        # google sheet dates are written like "1-Jan-2025" or "15-Apr-2026"
                        is_correct_year = "2026" in emp_date
                        is_correct_month = any(m.lower() in emp_date.lower() for m in target_months)
                        date_ok = (is_correct_year and is_correct_month)
                    else:
                        # target_date_str is e.g. "30-Jul-2026". Check if day "30" and month "Jul" are in emp_date
                        day_clean = target_date_str.split('-')[0]
                        month_clean = target_date_str.split('-')[1]
                        date_ok = (day_clean in emp_date and month_clean.lower() in emp_date.lower())
                
                # Check tech match
                tech_ok = True
                if target_tech:
                    # Use a broader match, e.g. "account" matches "Accounts" or "accounting"
                    tech_ok = (target_tech.lower() in emp_tech or emp_tech in target_tech.lower())
                
                if date_ok and tech_ok:
                    matched_candidates.append(emp)

            if matched_candidates:
                import json

                # Always build BOTH groupings so the frontend can switch tabs
                # --- Technology breakdown ---
                tech_counts = {}
                for c in matched_candidates:
                    tech = (c.get('designation') or 'Unknown').strip()
                    tech_counts[tech] = tech_counts.get(tech, 0) + 1
                sorted_tech = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]

                # --- Status breakdown ---
                status_counts = {}
                for c in matched_candidates:
                    st = (c.get('status') or 'Unknown').strip()
                    status_counts[st] = status_counts.get(st, 0) + 1
                sorted_status = sorted(status_counts.items(), key=lambda x: x[1], reverse=True)

                # --- Per-technology status drill-down ---
                tech_breakdown = {}
                for c in matched_candidates:
                    tech = (c.get('designation') or 'Unknown').strip()
                    st = (c.get('status') or 'Unknown').strip()
                    if tech not in tech_breakdown:
                        tech_breakdown[tech] = {}
                    tech_breakdown[tech][st] = tech_breakdown[tech].get(st, 0) + 1

                chart_payload = {
                    "title": f"Candidates on {target_date_str or 'All Dates'}" + (f" \u2014 {target_tech.title()}" if target_tech else ""),
                    "total": len(matched_candidates),
                    "tech_data": {
                        "labels": [t[0] for t in sorted_tech],
                        "values": [t[1] for t in sorted_tech],
                        "tab_label": "By Technology"
                    },
                    "status_data": {
                        "labels": [s[0] for s in sorted_status],
                        "values": [s[1] for s in sorted_status],
                        "tab_label": "By Status"
                    },
                    "tech_breakdown": tech_breakdown,
                    "default_tab": "status" if target_tech else "tech"
                }

                if is_chart_query:
                    # User asked for a chart — show ONLY the chart, no table
                    response_text = f"Here is the visual chart for your query (Date: **{target_date_str or 'All'}**, Tech: **{target_tech.title() if target_tech else 'All Technologies'}**):\n\n[CHART_DATA: {json.dumps(chart_payload)}]"
                else:
                    # User asked for data — show table only
                    response_text = f"### 📊 Candidates Added Report\n\n"
                    response_text += f"Found **{len(matched_candidates)}** candidates matching your query (Date: **{target_date_str or 'All'}**, Tech: **{target_tech or 'All'}**):\n\n"
                    response_text += "| Candidate Name | Technology | Date Added | Status |\n"
                    response_text += "| :--- | :--- | :--- | :--- |\n"
                    for c in matched_candidates:
                        response_text += f"| **{c.get('name')}** | {c.get('designation')} | {c.get('joining_date')} | {c.get('status')} |\n"
            else:
                response_text = f"No candidates found matching the query for Date: **{target_date_str or 'Any'}** and Tech: **{target_tech or 'Any'}**."
                
            return {"response": response_text, "steps": steps}


        # 1. Search / Find Employee
        target_name = None
        if "find" in words or "search" in words:
            idx = words.index("find") if "find" in words else words.index("search")
            if idx + 1 < len(words):
                name_words = [w for w in words[idx+1:] if w not in ["employee", "the", "for", "named"]]
                if name_words:
                    target_name = " ".join(name_words).title()
        else:
            # Check if query contains any candidate's name from the sheet
            try:
                import asyncio
                _res = asyncio.get_event_loop().run_until_complete(
                    mcp_client.execute_tool("read_sheet", {"sheet_name": "Master Recruitment Tracker 2026"})
                ) if not asyncio.get_event_loop().is_running() else None
                # In async context, use already-loaded sheet data via synchronous helper
                if _res is None:
                    # Already in async context — use sync path via mcp_client's tool fn directly
                    import sys, os
                    _srv_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp-server"))
                    if _srv_dir not in sys.path:
                        sys.path.insert(0, _srv_dir)
                    from sheets_helper import GoogleSheetsHelper as _GSH  # type: ignore
                    all_emps = _GSH().read_sheet("Master Recruitment Tracker 2026")
                else:
                    all_emps = _res if isinstance(_res, list) else _res.get("data", [])
                for emp in all_emps:
                    emp_name = emp.get("name", "").strip()
                    if emp_name and emp_name.lower() in msg_lower:
                        target_name = emp_name
                        break
            except Exception:
                pass
            
            # Fallback: if it's a simple query (1-3 words) and doesn't match other commands, treat as a name lookup
            if not target_name and len(words) <= 3 and not any(k in msg_lower for k in ["policy", "rules", "handbook", "hours", "leave", "send", "extension", "offer", "letter"]):
                target_name = message.strip()

        if target_name:
            args = {"name": target_name}
            res = await mcp_client.execute_tool("search_employee", args)
            log_audit(email, "search_employee", args, res)
            steps.append({"tool": "search_employee", "arguments": args, "status": "success", "response": res})
            
            if isinstance(res, list) and len(res) > 0:
                emp = res[0]
                response_text = (
                    f"### 📋 Candidate Profile: {emp.get('name')}\n\n"
                    f"| Field | Detail |\n"
                    f"| :--- | :--- |\n"
                    f"| **No. / ID** | {emp.get('employee_id')} |\n"
                    f"| **Email ID** | {emp.get('email')} |\n"
                    f"| **Contact number** | {emp.get('contact_number') or 'N/A'} |\n"
                    f"| **Status** | **{emp.get('status')}** |\n"
                    f"| **Recruiter Name** | {emp.get('recruiter_name') or 'N/A'} |\n"
                    f"| **Accountable** | {emp.get('accountable') or 'N/A'} |\n"
                    f"| **Technology (Job Title)** | {emp.get('designation')} |\n"
                    f"| **Tech/Non Tech** | {emp.get('tech_non_tech') or 'N/A'} |\n"
                    f"| **Opening For** | {emp.get('department') or 'N/A'} |\n"
                    f"| **Source** | {emp.get('source') or 'N/A'} |\n"
                    f"| **Date Applied** | {emp.get('joining_date')} |\n"
                    f"| **Month** | {emp.get('month') or 'N/A'} |\n"
                    f"| **Total Experience** | {emp.get('total_experience') or 'N/A'} |\n"
                    f"| **Relevant Experience** | {emp.get('relevant_experience') or 'N/A'} |\n"
                    f"| **Current Company** | {emp.get('current_company') or 'N/A'} |\n"
                    f"| **Current CTC** | {emp.get('current_ctc') or 'N/A'} |\n"
                    f"| **Expected CTC** | {emp.get('expected_ctc') or 'N/A'} |\n"
                    f"| **Notice Period** | {emp.get('notice_period') or 'N/A'} Days/Months |\n"
                    f"| **Location** | {emp.get('location') or 'N/A'} |\n"
                    f"| **Job Change Reason** | {emp.get('job_change_reason') or 'N/A'} |\n"
                    f"| **1st Round Mode** | {emp.get('interview_mode_1st') or 'N/A'} (Date: {emp.get('interview_date_1st') or 'N/A'}) |\n"
                    f"| **Interviewer (1st Round)** | {emp.get('interviewer_1st') or 'N/A'} (Result: {emp.get('status_1st') or 'N/A'}) |\n"
                    f"| **2nd/Final Round Mode** | {emp.get('interview_mode_2nd') or 'N/A'} (Date: {emp.get('interview_date_2nd') or 'N/A'}) |\n"
                    f"| **Interviewer (2nd Round)** | {emp.get('interviewer_2nd') or 'N/A'} (Result: {emp.get('status_2nd') or 'N/A'}) |\n"
                    f"| **CTC Offered** | {emp.get('ctc_offered') or 'N/A'} (Joining: {emp.get('offered_joining_date') or 'N/A'}) |\n"
                    f"| **Vendor Name** | {emp.get('vendor_name') or 'N/A'} |\n"
                    f"| **Remarks** | *{emp.get('recruiters_remarks') or 'None'}* |\n"
                )
            else:
                response_text = f"I couldn't find any employee matching '{target_name}' in your Google Sheet."
            return {"response": response_text, "steps": steps}

        # 2. Send / Create Extension Letter
        elif "extension" in msg_lower:
            if not is_privileged:
                return {
                    "response": f"Access Denied: Your role ({role}) does not have permission to generate or send contract extensions.",
                    "steps": []
                }
            # extract name or default
            target_name = "Rahul"
            for w in words:
                if w not in ["send", "his", "her", "extension", "letter", "for", "create", "generate", "to", "him", "employee"]:
                    target_name = w.title()
                    break
            
            # Step 1: Find Employee
            args1 = {"name": target_name}
            res1 = await mcp_client.execute_tool("search_employee", args1)
            steps.append({"tool": "search_employee", "arguments": args1, "status": "success", "response": res1})
            
            emp_id = None
            emp_email = "employee@company.com"
            emp_name = target_name
            if isinstance(res1, list) and len(res1) > 0:
                emp_id = res1[0].get("employee_id")
                emp_email = res1[0].get("email", emp_email)
                emp_name = res1[0].get("name", emp_name)
            
            if not emp_id:
                return {
                    "response": f"I couldn't find any employee named '{target_name}' to generate an extension letter.",
                    "steps": steps
                }

            # Step 2: Generate extension
            args2 = {"employee_id": emp_id}
            res2 = await mcp_client.execute_tool("generate_extension_letter", args2)
            steps.append({"tool": "generate_extension_letter", "arguments": args2, "status": "success", "response": res2})
            
            email_draft = {
                "to": emp_email,
                "subject": "Employment Contract Extension",
                "body": (
                    f"Hi {emp_name},\n\n"
                    f"We are pleased to inform you that your employment contract with Aetheris has been extended. "
                    f"Please find attached your extension letter for your records."
                )
            }
            
            response_text = (
                f"I have searched for {emp_name} ({emp_id}) and generated their contract extension letter PDF. "
                "Before sending, please review the drafted email below and approve it."
            )
            return {
                "response": response_text,
                "steps": steps,
                "email_approval_required": True,
                "email_draft": email_draft
            }

        # 3. Maternity / Leave balance
        elif "maternity" in msg_lower or "leave" in msg_lower:
            # Check if requesting specific employee leave balance
            target_name = None
            for w in words:
                if w not in ["show", "get", "leave", "balance", "for", "maternity", "who", "is", "on"]:
                    target_name = w.title()
                    break
            
            if target_name:
                # Find employee first
                args1 = {"name": target_name}
                res1 = await mcp_client.execute_tool("search_employee", args1)
                steps.append({"tool": "search_employee", "arguments": args1, "status": "success", "response": res1})
                if isinstance(res1, list) and len(res1) > 0:
                    emp_id = res1[0].get("employee_id")
                    args2 = {"employee_id": emp_id}
                    res2 = await mcp_client.execute_tool("get_leave_balance", args2)
                    steps.append({"tool": "get_leave_balance", "arguments": args2, "status": "success", "response": res2})
                    response_text = f"Leave balance details for {target_name} ({emp_id}): {json.dumps(res2, indent=1)}"
                else:
                    response_text = f"I couldn't find any employee named '{target_name}' to query leave balance."
                # General list sheets read
                args = {"sheet_name": "Master Recruitment Tracker 2026"}
                res = await mcp_client.execute_tool("read_sheet", args)
                steps.append({"tool": "read_sheet", "arguments": args, "status": "success", "response": res})
                maternity_emps = []
                if isinstance(res, list):
                    maternity_emps = [emp.get("name") for emp in res if "maternity" in str(emp.get("status", "")).lower() or "maternity" in str(emp.get("status_description", "")).lower()]
                
                if maternity_emps:
                    response_text = f"Based on the Google Sheet, the following employees are on maternity leave: {', '.join(maternity_emps)}."
                else:
                    response_text = "According to our sheets database, there are currently no employees listed on maternity leave."
            
            return {"response": response_text, "steps": steps}

        # 4. Salaryslip / calculate salary
        elif "salary" in msg_lower:
            if not is_privileged:
                return {
                    "response": f"Access Denied: Your role ({role}) does not have permission to view salary details.",
                    "steps": []
                }
            target_name = None
            for w in words:
                if w not in ["show", "get", "salary", "slip", "for", "calculate", "of", "june", "july"]:
                    target_name = w.title()
                    break
            if not target_name:
                target_name = "Rahul"
                
            args1 = {"name": target_name}
            res1 = await mcp_client.execute_tool("search_employee", args1)
            steps.append({"tool": "search_employee", "arguments": args1, "status": "success", "response": res1})
            
            emp_id = None
            if isinstance(res1, list) and len(res1) > 0:
                emp_id = res1[0].get("employee_id")
                emp_name = res1[0].get("name")
                
            if not emp_id:
                return {
                    "response": f"I couldn't find any employee named '{target_name}' to calculate salary.",
                    "steps": steps
                }
                
            args2 = {"employee_id": emp_id}
            res2 = await mcp_client.execute_tool("calculate_salary", args2)
            steps.append({"tool": "calculate_salary", "arguments": args2, "status": "success", "response": res2})
            
            # Generate salary slip as well if prompt asks for "slip"
            if "slip" in msg_lower:
                args3 = {"employee_id": emp_id}
                res3 = await mcp_client.execute_tool("generate_salary_slip", args3)
                steps.append({"tool": "generate_salary_slip", "arguments": args3, "status": "success", "response": res3})
                response_text = f"I have calculated the salary and generated a salary slip PDF for {emp_name}. You can download the PDF below."
            else:
                response_text = f"Salary details for {emp_name} ({emp_id}): Base is ${res2.get('base_salary')}, Net Take-Home is ${res2.get('net_salary')}."
                
            return {"response": response_text, "steps": steps}

        # 5. Pending documents
        elif "pending" in msg_lower or "document" in msg_lower:
            res = await mcp_client.execute_tool("list_pending_documents", {})
            steps.append({"tool": "list_pending_documents", "arguments": {}, "status": "success", "response": res})
            if isinstance(res, list) and len(res) > 0:
                doc_lines = [f"- {emp.get('name')}: {', '.join(emp.get('pending_documents', []))}" for emp in res]
                response_text = "Here are the employees with pending documents:\n" + "\n".join(doc_lines)
            else:
                response_text = "All employees have submitted their required documents. There are no pending documents."
            return {"response": response_text, "steps": steps}

        # 6. Birthdays
        elif "birthday" in msg_lower:
            res = await mcp_client.execute_tool("list_birthdays", {})
            steps.append({"tool": "list_birthdays", "arguments": {}, "status": "success", "response": res})
            if isinstance(res, list) and len(res) > 0:
                bday_lines = [f"- {emp.get('name')}: {emp.get('birthday')}" for emp in res]
                response_text = "Here are the employee birthdays:\n" + "\n".join(bday_lines)
            else:
                response_text = "No birthdays recorded in the sheet database."
            return {"response": response_text, "steps": steps}

        # 7. Fallback greeting
        else:
            response_text = (
                f"Hello! I am your HR Copilot. I have access to your live Google Sheet database! "
                f"Try asking: 'Find Hardik', 'Create extension letter for Rahul', or 'Who has pending documents?'"
            )

        return {
            "response": response_text,
            "steps": steps
        }

agent_service = AgentService()
