import os
import json
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sheets_helper")

# Mock database initialized with realistic records for instant demo capability
MOCK_EMPLOYEES = [
    {
        "employee_id": "EMP001",
        "name": "Rahul Patel",
        "email": "rahul.patel@company.com",
        "role": "Employee",
        "department": "Engineering",
        "designation": "Senior Frontend Developer",
        "joining_date": "2024-01-15",
        "pending_documents": ["Degree Certificate", "Signed Offer Letter"],
        "birthday": "08-12",
        "status": "Active"
    },
    {
        "employee_id": "EMP002",
        "name": "Priya Sharma",
        "email": "priya.sharma@company.com",
        "role": "HR",
        "department": "Human Resources",
        "designation": "HR Manager",
        "joining_date": "2023-05-10",
        "pending_documents": [],
        "birthday": "07-31",
        "status": "Active"
    },
    {
        "employee_id": "EMP003",
        "name": "Amit Verma",
        "email": "amit.verma@company.com",
        "role": "Manager",
        "department": "Engineering",
        "designation": "Engineering Manager",
        "joining_date": "2022-11-01",
        "pending_documents": [],
        "birthday": "11-23",
        "status": "Active"
    },
    {
        "employee_id": "EMP004",
        "name": "Sneha Reddy",
        "email": "sneha.reddy@company.com",
        "role": "Employee",
        "department": "Marketing",
        "designation": "Marketing Specialist",
        "joining_date": "2025-06-01",
        "pending_documents": ["Previous Relieving Letter"],
        "birthday": "02-14",
        "status": "Maternity Leave"
    }
]

MOCK_ATTENDANCE = [
    {"employee_id": "EMP001", "date": "2026-07-29", "status": "Present"},
    {"employee_id": "EMP002", "date": "2026-07-29", "status": "Present"},
    {"employee_id": "EMP003", "date": "2026-07-29", "status": "Present"},
    {"employee_id": "EMP004", "date": "2026-07-29", "status": "Leave"}
]

MOCK_SALARY = [
    {"employee_id": "EMP001", "month": "June", "base_salary": 85000, "allowances": 15000, "deductions": 5000, "net_salary": 95000},
    {"employee_id": "EMP002", "month": "June", "base_salary": 75000, "allowances": 10000, "deductions": 4000, "net_salary": 81000},
    {"employee_id": "EMP003", "month": "June", "base_salary": 120000, "allowances": 20000, "deductions": 10000, "net_salary": 130000},
    {"employee_id": "EMP004", "month": "June", "base_salary": 60000, "allowances": 8000, "deductions": 3000, "net_salary": 65000}
]

MOCK_LEAVE = [
    {"employee_id": "EMP001", "leave_type": "Casual", "balance": 12, "approved": 3, "pending": 1},
    {"employee_id": "EMP002", "leave_type": "Sick", "balance": 8, "approved": 2, "pending": 0},
    {"employee_id": "EMP003", "leave_type": "Annual", "balance": 18, "approved": 5, "pending": 0},
    {"employee_id": "EMP004", "leave_type": "Maternity", "balance": 0, "approved": 90, "pending": 0}
]

MOCK_CLIENTS = [
    {"client_id": "CLI001", "name": "Global Tech Corp", "contact_email": "procurement@globaltech.com", "status": "Active"},
    {"client_id": "CLI002", "name": "Innovate LLC", "contact_email": "partners@innovate.com", "status": "Active"}
]

MOCK_PROJECTS = [
    {"project_id": "PRJ101", "name": "HR Portal Upgrade", "client_id": "CLI001", "manager_id": "EMP003", "status": "In Progress"},
    {"project_id": "PRJ102", "name": "Ad Campaign Q3", "client_id": "CLI002", "manager_id": "EMP003", "status": "Planning"}
]

MOCK_SETTINGS = {
    "company_name": "Aetheris HR Services Ltd",
    "branding_color": "#4F46E5",
    "fiscal_year_start": "04-01"
}


class GoogleSheetsHelper:
    def __init__(self):
        # Load env variables from root .env
        import os
        from dotenv import load_dotenv
        possible_envs = [
            os.path.abspath(".env"),
            os.path.abspath("../.env"),
            os.path.abspath("../../.env"),
            os.path.abspath("../../../.env")
        ]
        for env_p in possible_envs:
            if os.path.exists(env_p):
                load_dotenv(env_p)
                break

        self.sheet_id = os.getenv("GOOGLE_SHEET_ID", "mock-sheet-id")
        
        creds_p = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "credentials.json")
        if not os.path.isabs(creds_p):
            for prefix in [".", "..", "../..", "../../.."]:
                p = os.path.abspath(os.path.join(prefix, creds_p))
                if os.path.exists(p):
                    creds_p = p
                    break
                    
        self.creds_path = creds_p
        self.is_mock = self.sheet_id == "mock-sheet-id" or not os.path.exists(self.creds_path)
        
        if self.is_mock:
            logger.info("Using local mock sheets database engine.")
            self.employees = MOCK_EMPLOYEES
            self.attendance = MOCK_ATTENDANCE
            self.salary = MOCK_SALARY
            self.leave = MOCK_LEAVE
            self.clients = MOCK_CLIENTS
            self.projects = MOCK_PROJECTS
            self.settings = MOCK_SETTINGS
        else:
            logger.info("Initializing Google Sheets API connection.")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                scopes = ['https://www.googleapis.com/auth/spreadsheets']
                self.creds = service_account.Credentials.from_service_account_file(self.creds_path, scopes=scopes)
                self.service = build('sheets', 'v4', credentials=self.creds)
            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets API: {e}. Falling back to mock engine.")
                self.is_mock = True
                self.employees = MOCK_EMPLOYEES
                self.attendance = MOCK_ATTENDANCE
                self.salary = MOCK_SALARY
                self.leave = MOCK_LEAVE
                self.clients = MOCK_CLIENTS
                self.projects = MOCK_PROJECTS
                self.settings = MOCK_SETTINGS

    def read_sheet(self, sheet_name: str, sheet_id: Optional[str] = None) -> List[Dict[str, Any]]:
        active_sheet_id = sheet_id or self.sheet_id
        if self.is_mock and (active_sheet_id == "mock-sheet-id" or not hasattr(self, 'service')):
            attr_name = sheet_name.lower()
            if hasattr(self, attr_name):
                val = getattr(self, attr_name)
                if isinstance(val, dict):
                    return [val]
                return val
            return []
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=active_sheet_id, range=f"{sheet_name}!A:Z"
            ).execute()
            rows = result.get('values', [])
            if not rows:
                return []
            headers = [h.strip() for h in rows[0]]
            data = []
            for row in rows[1:]:
                row_dict = {}
                for idx, val in enumerate(row):
                    if idx < len(headers):
                        row_dict[headers[idx]] = val.strip() if isinstance(val, str) else val
                # Filter out completely empty or uninitialized rows
                if row_dict and any(v.strip() if isinstance(v, str) else v for v in row_dict.values()):
                    data.append(row_dict)

            # Check if this is the custom layout
            if "Candidate Name" in headers or "Email ID" in headers:
                mapped_data = []
                for entry in data:
                    raw_name = entry.get("Candidate Name", "").strip()
                    raw_email_id = entry.get("Email ID", "").strip()
                    
                    if not raw_name and not raw_email_id:
                        continue
                    if (raw_name.lower() in ["name", "candidate name", "offered", "joined"]) or (raw_email_id.lower() in ["email id"]):
                        continue
                    
                    # Self-healing email detector
                    email = "no-email@company.com"
                    for val in entry.values():
                        if isinstance(val, str) and "@" in val:
                            email = val.strip()
                            break
                    if "@" in raw_email_id:
                        email = raw_email_id
                        
                    # Determine candidate name
                    if raw_name:
                        name = raw_name
                    elif "@" in raw_email_id:
                        prefix = raw_email_id.split("@")[0]
                        name = "".join([c for c in prefix if c.isalpha()]).title()
                    else:
                        name = raw_email_id
                        
                    mapped_entry = {
                        "employee_id": entry.get("No.", entry.get("Date", "EMP")),
                        "name": name,
                        "email": email,
                        "designation": entry.get("Job Title", "Developer"),
                        "department": entry.get("Opening For ( Inhouse / Client)", "Engineering"),
                        "joining_date": entry.get("Date", ""),
                        "pending_documents": [],
                        "birthday": "01-01",
                        "status": entry.get("Status", "Active"),
                        
                        # Store all of the remaining custom columns
                        "month": entry.get("Month", ""),
                        "accountable": entry.get("Accountable", ""),
                        "recruiter_name": entry.get("Recruiter Name", ""),
                        "tech_non_tech": entry.get("Tech/Non Tech", ""),
                        "source": entry.get("Source ✅", ""),
                        "contact_number": entry.get("Contact number", ""),
                        "total_experience": entry.get("Total Experience", ""),
                        "relevant_experience": entry.get("Relevant Experience", ""),
                        "current_ctc": entry.get("Current CTC", ""),
                        "expected_ctc": entry.get("Expected CTC", ""),
                        "notice_period": entry.get("Notice Period", ""),
                        "location": entry.get("Location", ""),
                        "job_change_reason": entry.get("Job Change Reason", ""),
                        "recruiters_remarks": entry.get("Recruiter's Remarks", ""),
                        "current_company": entry.get("Current Company Name", ""),
                        "interview_mode_1st": entry.get("Interview Mode (1st Round)", ""),
                        "interview_date_1st": entry.get("1st Round Interview Date(( 01-Jan-2026))", ""),
                        "interviewer_1st": entry.get("Interviewer (1st Round)", ""),
                        "status_1st": entry.get("Status (1st Round)", ""),
                        "interview_date_2nd": entry.get("Interview (2nd / Final Round) Date", ""),
                        "interview_mode_2nd": entry.get("Interview Mode (2nd Round)", ""),
                        "interviewer_2nd": entry.get("Interviewer (2nd / Final Round)", ""),
                        "status_2nd": entry.get("Status (2nd / Final Round)", ""),
                        "offered_joining_date": entry.get("Joining Date", ""),
                        "ctc_offered": entry.get("CTC Offered", ""),
                        "vendor_name": entry.get("Vendor Name", "")
                    }
                    mapped_data.append(mapped_entry)
                return mapped_data

            return data
        except Exception as e:
            logger.error(f"Error reading sheet {sheet_name} from spreadsheet {active_sheet_id}: {e}")
            return []

    def update_sheet(self, sheet_name: str, row: int, column: str, value: Any, sheet_id: Optional[str] = None) -> bool:
        active_sheet_id = sheet_id or self.sheet_id
        if self.is_mock and (active_sheet_id == "mock-sheet-id" or not hasattr(self, 'service')):
            # Simple updates on in-memory mock for demonstration
            logger.info(f"[MOCK] Sheet '{sheet_name}' updated: row {row}, col {column} = {value}")
            return True
        try:
            body = {'values': [[value]]}
            self.service.spreadsheets().values().update(
                spreadsheetId=active_sheet_id,
                range=f"{sheet_name}!{column}{row}",
                valueInputOption="RAW",
                body=body
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating sheet {sheet_name} on spreadsheet {active_sheet_id}: {e}")
            return False

    def search_employee(self, name: str, sheet_id: Optional[str] = None) -> List[Dict[str, Any]]:
        employees = self.read_sheet("Master Recruitment Tracker 2026", sheet_id=sheet_id)
        return [emp for emp in employees if name.lower() in emp.get("name", "").lower()]

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        employees = self.read_sheet("Master Recruitment Tracker 2026")
        for emp in employees:
            if emp.get("employee_id") == employee_id:
                return emp
        return None

    def search_client(self, name: str) -> List[Dict[str, Any]]:
        clients = self.read_sheet("clients")
        return [c for c in clients if name.lower() in c.get("name", "").lower()]

    def list_birthdays(self) -> List[Dict[str, Any]]:
        employees = self.read_sheet("Master Recruitment Tracker 2026")
        return [{"name": emp["name"], "birthday": emp["birthday"], "email": emp["email"]} for emp in employees if "birthday" in emp]

    def list_pending_documents(self) -> List[Dict[str, Any]]:
        employees = self.read_sheet("Master Recruitment Tracker 2026")
        res = []
        for emp in employees:
            docs = emp.get("pending_documents", [])
            # Support both list and comma-separated string from sheet
            if isinstance(docs, str):
                docs = [d.strip() for d in docs.split(",") if d.strip()]
            if docs:
                res.append({"name": emp["name"], "employee_id": emp["employee_id"], "pending_documents": docs})
        return res

    def get_leave_balance(self, employee_id: str) -> List[Dict[str, Any]]:
        leaves = self.read_sheet("leave")
        return [l for l in leaves if l.get("employee_id") == employee_id]

    def calculate_salary(self, employee_id: str) -> Optional[Dict[str, Any]]:
        salaries = self.read_sheet("salary")
        for s in salaries:
            if s.get("employee_id") == employee_id:
                # convert strings to float/int if reading from live sheet
                base = float(s.get("base_salary", 0))
                allowances = float(s.get("allowances", 0))
                deductions = float(s.get("deductions", 0))
                return {
                    "employee_id": employee_id,
                    "month": s.get("month", "Current"),
                    "base_salary": base,
                    "allowances": allowances,
                    "deductions": deductions,
                    "net_salary": base + allowances - deductions
                }
        return None
