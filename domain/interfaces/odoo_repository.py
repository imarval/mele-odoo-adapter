from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..entities.odoo_record import OdooRecord, OdooSyncResult, OdooOperation


class IOdooRepository(ABC):
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        pass
    
    @abstractmethod
    async def create_record(self, model: str, values: Dict[str, Any]) -> OdooSyncResult:
        pass
    
    @abstractmethod
    async def update_record(self, model: str, record_id: int, values: Dict[str, Any]) -> OdooSyncResult:
        pass
    
    @abstractmethod
    async def delete_record(self, model: str, record_id: int) -> OdooSyncResult:
        pass
    
    @abstractmethod
    async def search_records(self, model: str, domain: List[tuple], limit: int = 100) -> List[int]:
        pass
    
    @abstractmethod
    async def read_records(self, model: str, record_ids: List[int], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def search_read(self, model: str, domain: List[tuple], fields: Optional[List[str]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def execute_operation(self, operation: OdooOperation) -> OdooSyncResult:
        pass
    
    @abstractmethod
    async def get_external_id(self, model: str, record_id: int) -> Optional[str]:
        pass
    
    @abstractmethod
    async def find_by_external_id(self, external_id: str) -> Optional[OdooRecord]:
        pass
    
    @abstractmethod
    async def set_external_id(self, model: str, record_id: int, external_id: str) -> bool:
        pass