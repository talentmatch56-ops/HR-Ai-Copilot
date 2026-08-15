import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
service = build('sheets', 'v4', credentials=creds)

try:
    result = service.spreadsheets().values().get(
        spreadsheetId='1PFnlXR42tsxS9UAIqf4vpEUfe-b0G9GasNNEmk6EIjc',
        range='Master Recruitment Tracker 2026!A:Z'
    ).execute()
    print("Success! Got rows:", len(result.get('values', [])))
except Exception as e:
    print("Error:", e)
