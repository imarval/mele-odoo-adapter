import asyncio
import logging
from typing import Callable, Optional, Any
from signalrcore.hub_connection_builder import HubConnectionBuilder
from signalrcore.messages.completion_message import CompletionMessage

from ...domain.interfaces.signalr_client import ISignalRClient
from ...domain.entities.integration_event import IntegrationEvent


class SignalRClientImpl(ISignalRClient):
    def __init__(self):
        self.connection = None
        self.url: Optional[str] = None
        self.subscription_id: Optional[str] = None
        self.is_listening = False
        self.logger = logging.getLogger(__name__)
        
        self.event_received_handlers = []
        self.connection_error_handlers = []
        self.disconnected_handlers = []
    
    async def connect(self, url: str, subscription_id: str) -> bool:
        try:
            self.url = url
            self.subscription_id = subscription_id
            
            self.connection = (
                HubConnectionBuilder()
                .with_url(url)
                .with_automatic_reconnect({
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 5
                })
                .build()
            )
            
            self._setup_connection_handlers()
            
            self.connection.start()
            
            await self.join_tenant_group(subscription_id)
            
            self.logger.info(f"Connected to SignalR hub: {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SignalR hub: {str(e)}")
            return False
    
    async def disconnect(self) -> None:
        try:
            if self.connection and self.connection.transport.state.name == "connected":
                if self.subscription_id:
                    await self.leave_tenant_group(self.subscription_id)
                
                self.connection.stop()
                self.logger.info("Disconnected from SignalR hub")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {str(e)}")
    
    async def is_connected(self) -> bool:
        return (
            self.connection is not None 
            and self.connection.transport.state.name == "connected"
        )
    
    async def join_tenant_group(self, subscription_id: str) -> bool:
        try:
            if not await self.is_connected():
                return False
            
            result = self.connection.send("JoinTenantGroup", [subscription_id])
            
            if isinstance(result, CompletionMessage) and not result.error:
                self.logger.info(f"Joined tenant group: tenant_{subscription_id}")
                return True
            else:
                self.logger.error(f"Failed to join tenant group: {result.error if hasattr(result, 'error') else 'Unknown error'}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error joining tenant group: {str(e)}")
            return False
    
    async def leave_tenant_group(self, subscription_id: str) -> bool:
        try:
            if not await self.is_connected():
                return False
            
            result = self.connection.send("LeaveTenantGroup", [subscription_id])
            
            if isinstance(result, CompletionMessage) and not result.error:
                self.logger.info(f"Left tenant group: tenant_{subscription_id}")
                return True
            else:
                self.logger.error(f"Failed to leave tenant group: {result.error if hasattr(result, 'error') else 'Unknown error'}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error leaving tenant group: {str(e)}")
            return False
    
    def on_event_received(self, handler: Callable[[IntegrationEvent], None]) -> None:
        self.event_received_handlers.append(handler)
    
    def on_connection_error(self, handler: Callable[[str], None]) -> None:
        self.connection_error_handlers.append(handler)
    
    def on_disconnected(self, handler: Callable[[], None]) -> None:
        self.disconnected_handlers.append(handler)
    
    async def start_listening(self) -> None:
        self.is_listening = True
        self.logger.info("Started listening for SignalR events")
    
    async def stop_listening(self) -> None:
        self.is_listening = False
        self.logger.info("Stopped listening for SignalR events")
    
    def _setup_connection_handlers(self):
        if not self.connection:
            return
        
        self.connection.on("EventReceived", self._handle_event_received)
        self.connection.on_open(self._handle_connection_opened)
        self.connection.on_close(self._handle_connection_closed)
        self.connection.on_error(self._handle_connection_error)
    
    def _handle_event_received(self, event_data):
        try:
            if not self.is_listening:
                return
            
            self.logger.debug(f"Received SignalR event: {event_data}")
            
            if isinstance(event_data, list) and len(event_data) > 0:
                event_data = event_data[0]
            
            integration_event = IntegrationEvent.from_dict(event_data)
            
            for handler in self.event_received_handlers:
                try:
                    handler(integration_event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error processing received event: {str(e)}")
    
    def _handle_connection_opened(self):
        self.logger.info("SignalR connection opened")
    
    def _handle_connection_closed(self):
        self.logger.warning("SignalR connection closed")
        for handler in self.disconnected_handlers:
            try:
                handler()
            except Exception as e:
                self.logger.error(f"Error in disconnected handler: {str(e)}")
    
    def _handle_connection_error(self, error):
        error_msg = str(error) if error else "Unknown connection error"
        self.logger.error(f"SignalR connection error: {error_msg}")
        
        for handler in self.connection_error_handlers:
            try:
                handler(error_msg)
            except Exception as e:
                self.logger.error(f"Error in connection error handler: {str(e)}")