from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.integration_event import IntegrationEvent


class IEventRepository(ABC):
    
    @abstractmethod
    async def save_event(self, event: IntegrationEvent) -> bool:
        pass
    
    @abstractmethod
    async def get_event_by_id(self, event_id: str) -> Optional[IntegrationEvent]:
        pass
    
    @abstractmethod
    async def get_events_by_entity_type(self, entity_type: str, limit: int = 100) -> List[IntegrationEvent]:
        pass
    
    @abstractmethod
    async def get_pending_events(self, limit: int = 100) -> List[IntegrationEvent]:
        pass
    
    @abstractmethod
    async def mark_event_as_processed(self, event_id: str) -> bool:
        pass
    
    @abstractmethod
    async def mark_event_as_failed(self, event_id: str, error_message: str) -> bool:
        pass
    
    @abstractmethod
    async def get_failed_events(self, limit: int = 100) -> List[IntegrationEvent]:
        pass
    
    @abstractmethod
    async def cleanup_old_events(self, older_than: datetime) -> int:
        pass