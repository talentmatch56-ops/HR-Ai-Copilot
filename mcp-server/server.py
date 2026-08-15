import os
import json
import logging
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP

from sheets_helper import GoogleSheetsHelper
from gmail_helper import GmailHelper
from doc_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# Instantiate FastMCP server
mcp = FastMCP("hr-ai-copilot-mcp")

# Initialize assistants
sheets = GoogleSheetsHelper()
gmail = GmailHelper()
docs = DocumentGenerator()

@mcp.tool()
def search_employee(name: str, sheet_id: Optional[str] = None) -> str:
    """Search for employees by name in the Google Sheets database."""
    logger.info(f"Tool search_employee called with name={name}, sheet_id={sheet_id}")
    results = sheets.search_employee(name, sheet_id=sheet_id)
    return json.dumps(results, indent=2)

@mcp.tool()
def get_employee(employee_id: str, sheet_id: Optional[str] = None) -> str:
    """Retrieve detailed information for a specific employee by ID."""
    logger.info(f"Tool get_employee called with employee_id={employee_id}, sheet_id={sheet_id}")
    # get_employee in sheets helper doesn't support sheet_id yet, let's implement it inside sheets helper if needed or do it here:
    employees = sheets.read_sheet("Master Recruitment Tracker 2026", sheet_id=sheet_id)
    result = None
    for emp in employees:
        if emp.get("employee_id") == employee_id:
            result = emp
            break
    if not result:
        return json.dumps({"status": "error", "message": f"Employee {employee_id} not found."})
    return json.dumps(result, indent=2)

@mcp.tool()
def search_google_sheet(query: str, sheet_id: Optional[str] = None) -> str:
    """Search across all major spreadsheets (employees, clients, projects) for matching queries."""
    logger.info(f"Tool search_google_sheet called with query={query}, sheet_id={sheet_id}")
    results = []
    for category in ["Master Recruitment Tracker 2026", "clients", "projects"]:
        data = sheets.read_sheet(category, sheet_id=sheet_id)
        for entry in data:
            if any(query.lower() in str(val).lower() for val in entry.values()):
                entry["_sheet"] = category
                results.append(entry)
    return json.dumps(results, indent=2)

@mcp.tool()
def read_sheet(sheet_name: str, sheet_id: Optional[str] = None) -> str:
    """Read all entries/rows from a specific spreadsheet sheet."""
    logger.info(f"Tool read_sheet called with sheet_name={sheet_name}, sheet_id={sheet_id}")
    results = sheets.read_sheet(sheet_name, sheet_id=sheet_id)
    return json.dumps(results, indent=2)

@mcp.tool()
def update_sheet(row: int, column: str, value: str, sheet_name: str = "Master Recruitment Tracker 2026", sheet_id: Optional[str] = None) -> str:
    """Update a specific cell value (by row and column letter/header) in a spreadsheet."""
    logger.info(f"Tool update_sheet called: sheet={sheet_name}, row={row}, col={column}, val={value}, sheet_id={sheet_id}")
    success = sheets.update_sheet(sheet_name, row, column, value, sheet_id=sheet_id)
    return json.dumps({"status": "success" if success else "error"}, indent=2)

@mcp.tool()
def send_email(to: str, subject: str, body: str, employee_name: Optional[str] = None, client_name: Optional[str] = None, project_name: Optional[str] = None, manager_name: Optional[str] = None, salary: Optional[str] = None) -> str:
    """Send a professional email (supports placeholding: employee_name, client_name, project_name, manager_name, salary)."""
    logger.info(f"Tool send_email called with to={to}, subject={subject}")
    placeholders = {}
    if employee_name: placeholders["employee_name"] = employee_name
    if client_name: placeholders["client_name"] = client_name
    if project_name: placeholders["project_name"] = project_name
    if manager_name: placeholders["manager_name"] = manager_name
    if salary: placeholders["salary"] = salary
    
    res = gmail.send_email(to, subject, body, placeholders)
    return json.dumps(res, indent=2)

@mcp.tool()
def generate_salary_slip(employee_id: str) -> str:
    """Generate a premium PDF salary slip for a specific employee."""
    logger.info(f"Tool generate_salary_slip called with employee_id={employee_id}")
    emp = sheets.get_employee(employee_id)
    if not emp:
        return json.dumps({"status": "error", "message": f"Employee {employee_id} not found."})
    
    salary = sheets.calculate_salary(employee_id)
    if not salary:
        # Provide default salary fallback for slip generation
        salary = {"employee_id": employee_id, "month": "June", "base_salary": 50000, "allowances": 5000, "deductions": 2000, "net_salary": 53000}
        
    res = docs.generate_salary_slip(emp, salary)
    return json.dumps(res, indent=2)

@mcp.tool()
def generate_offer_letter(employee_id: str) -> str:
    """Generate a formal PDF offer letter for a new/existing employee ID."""
    logger.info(f"Tool generate_offer_letter called with employee_id={employee_id}")
    emp = sheets.get_employee(employee_id)
    if not emp:
        return json.dumps({"status": "error", "message": f"Employee {employee_id} not found."})
    res = docs.generate_offer_letter(emp)
    return json.dumps(res, indent=2)

@mcp.tool()
def generate_extension_letter(employee_id: str) -> str:
    """Generate a PDF contract extension letter for a specific employee."""
    logger.info(f"Tool generate_extension_letter called with employee_id={employee_id}")
    emp = sheets.get_employee(employee_id)
    if not emp:
        return json.dumps({"status": "error", "message": f"Employee {employee_id} not found."})
    res = docs.generate_extension_letter(emp)
    return json.dumps(res, indent=2)

@mcp.tool()
def get_leave_balance(employee_id: str) -> str:
    """Get the current leave balance breakdown for an employee."""
    logger.info(f"Tool get_leave_balance called with employee_id={employee_id}")
    balance = sheets.get_leave_balance(employee_id)
    return json.dumps(balance, indent=2)

@mcp.tool()
def calculate_salary(employee_id: str) -> str:
    """Compute base, allowances, deductions, and net take-home salary of an employee."""
    logger.info(f"Tool calculate_salary called with employee_id={employee_id}")
    res = sheets.calculate_salary(employee_id)
    if not res:
        return json.dumps({"status": "error", "message": f"Salary records not found for {employee_id}."})
    return json.dumps(res, indent=2)

@mcp.tool()
def search_client(client_name: str) -> str:
    """Search for corporate client records by name."""
    logger.info(f"Tool search_client called with client_name={client_name}")
    res = sheets.search_client(client_name)
    return json.dumps(res, indent=2)

@mcp.tool()
def list_pending_documents() -> str:
    """List all employees who have missing or pending documentation (e.g. ID, certificates)."""
    logger.info("Tool list_pending_documents called")
    res = sheets.list_pending_documents()
    return json.dumps(res, indent=2)

@mcp.tool()
def list_birthdays() -> str:
    """List employee names and their upcoming birthdays for recognition purposes."""
    logger.info("Tool list_birthdays called")
    res = sheets.list_birthdays()
    return json.dumps(res, indent=2)

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """Search company policy documents, maternity leave policies, handbooks, and remote work rules."""
    logger.info(f"Tool search_knowledge_base called with query={query}")
    kb = [
        {
            "title": "Maternity Leave Policy",
            "content": "Employees are eligible for up to 90 calendar days of paid Maternity Leave. Applications must be submitted at least 4 weeks prior to the commencement date. Manager approval is required, and the HR department handles the final document compliance."
        },
        {
            "title": "Casual and Sick Leave Policies",
            "content": "Each employee is credited with 12 casual leave days and 8 sick leave days annually. Unused casual leaves expire at the end of the fiscal year, while sick leaves can be carried forward up to a maximum of 30 days."
        },
        {
            "title": "Office Working Hours & Remote Work",
            "content": "Our core operating hours are 9:00 AM to 6:00 PM local time. Under the hybrid model, employees can work remotely up to 2 days per week with manager approval."
        }
    ]
    
    matches = []
    query_words = set(query.lower().split())
    for doc in kb:
        doc_words = set(doc["content"].lower().replace(".", "").replace(",", "").split())
        intersection = query_words.intersection(doc_words)
        score = len(intersection) / len(query_words) if query_words else 0
        if score > 0.05:
            matches.append({"doc": doc, "score": score})
            
    matches.sort(key=lambda x: x["score"], reverse=True)
    results = [m["doc"] for m in matches[:2]]
    return json.dumps(results if results else kb[:1], indent=2)

@mcp.tool()
def update_employee_status(employee_id: str, new_status: str) -> str:
    """Update a candidate's status by finding their ID in the sheet dynamically."""
    logger.info(f"Tool update_employee_status called: id={employee_id}, status={new_status}")
    if sheets.is_mock:
        return json.dumps({"status": "success", "message": "[MOCK] Status updated."})
    try:
        result = sheets.service.spreadsheets().values().get(
            spreadsheetId=sheets.sheet_id, range="Master Recruitment Tracker 2026!A:Z"
        ).execute()
        rows = result.get('values', [])
        if not rows:
            return json.dumps({"status": "error", "message": "No rows found in sheet."})
            
        match_row = -1
        for idx, row in enumerate(rows):
            if row and row[0].strip() == employee_id.strip():
                match_row = idx + 1
                break
                
        if match_row == -1:
            return json.dumps({"status": "error", "message": f"Candidate with ID {employee_id} not found."})
            
        headers = [h.strip() for h in rows[0]]
        status_col_idx = -1
        for idx, h in enumerate(headers):
            if h == "Total Experience":
                status_col_idx = idx
                break
                
        if status_col_idx == -1:
            status_col_idx = 7
            
        col_letter = chr(65 + status_col_idx)
        res = sheets.update_sheet("Master Recruitment Tracker 2026", match_row, col_letter, new_status)
        return json.dumps({"status": "success" if res else "error", "row": match_row, "column": col_letter})
    except Exception as e:
        logger.error(f"Error in dynamic update_employee_status: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def create_pdf(filename: str, title: str, content: str) -> str:
    """Create a generic custom PDF document under the specified file name with a title and body text."""
    logger.info(f"Tool create_pdf called: file={filename}, title={title}")
    res = docs.create_custom_pdf(filename, title, content)
    return json.dumps(res, indent=2)

if __name__ == "__main__":
    # Start the FastMCP server over SSE / Stdio mode
    # For Docker / SSE, run: mcp dev server.py or run it directly
    mcp.run()
