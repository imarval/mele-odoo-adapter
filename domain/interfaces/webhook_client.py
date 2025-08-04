from abc import ABC, abstractmethod
from typing import Callable, Optional

from ..entities.integration_event import IntegrationEvent


class IWebhookClient(ABC):
    
    @abstractmethod
    async def start_server(self, host: str, port: int) -> None:
        pass
    
    @abstractmethod
    async def stop_server(self) -> None:
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        pass
    
    @abstractmethod
    def on_event_received(self, handler: Callable[[IntegrationEvent], None]) -> None:
        pass
    
    @abstractmethod
    def get_webhook_url(self) -> Optional[str]:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass