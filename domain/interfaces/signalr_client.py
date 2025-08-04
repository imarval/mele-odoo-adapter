from abc import ABC, abstractmethod
from typing import Callable, Optional, Any
import asyncio

from ..entities.integration_event import IntegrationEvent


class ISignalRClient(ABC):
    
    @abstractmethod
    async def connect(self, url: str, subscription_id: str) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        pass
    
    @abstractmethod
    async def join_tenant_group(self, subscription_id: str) -> bool:
        pass
    
    @abstractmethod
    async def leave_tenant_group(self, subscription_id: str) -> bool:
        pass
    
    @abstractmethod
    def on_event_received(self, handler: Callable[[IntegrationEvent], None]) -> None:
        pass
    
    @abstractmethod
    def on_connection_error(self, handler: Callable[[str], None]) -> None:
        pass
    
    @abstractmethod
    def on_disconnected(self, handler: Callable[[], None]) -> None:
        pass
    
    @abstractmethod
    async def start_listening(self) -> None:
        pass
    
    @abstractmethod
    async def stop_listening(self) -> None:
        pass