from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class OdooRecord:
    model: str
    record_id: Optional[int] = None
    values: Optional[Dict[str, Any]] = None
    external_id: Optional[str] = None
    
    def __post_init__(self):
        if self.values is None:
            self.values = {}


@dataclass  
class OdooSyncResult:
    success: bool
    record_id: Optional[int] = None
    external_id: Optional[str] = None
    message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class OdooOperation:
    operation_type: str  # 'create', 'write', 'unlink'
    model: str
    record_id: Optional[int] = None
    values: Optional[Dict[str, Any]] = None
    domain: Optional[list] = None
    
    def __post_init__(self):
        if self.values is None:
            self.values = {}
        if self.domain is None:
            self.domain = []