import json
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    user_role = Column(String(50), nullable=False)
    tool_name = Column(String(100), nullable=False, index=True)
    parameters = Column(Text, nullable=False)  # JSON serialized string
    response = Column(Text, nullable=True)     # JSON serialized string

    def to_dict(self):
        try:
            params = json.loads(self.parameters)
        except:
            params = self.parameters
            
        try:
            resp = json.loads(self.response) if self.response else None
        except:
            resp = self.response

        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user_email,
            "user_role": self.user_role,
            "tool": self.tool_name,
            "parameters": params,
            "response": resp
        }

class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content
        }

class RegisteredSheet(Base):
    __tablename__ = "registered_sheets"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sheet_id": self.sheet_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
