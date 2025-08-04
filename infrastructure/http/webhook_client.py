import asyncio
import logging
from typing import Callable, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, ValidationError

from ...domain.interfaces.webhook_client import IWebhookClient
from ...domain.entities.integration_event import IntegrationEvent


class WebhookEventModel(BaseModel):
    eventType: str
    entityType: str
    eventId: str
    timeStamp: str
    sourceSystem: Optional[dict] = None
    payload: Optional[dict] = None
    context: Optional[dict] = None


class WebhookClientImpl(IWebhookClient):
    def __init__(self):
        self.app = FastAPI(title="Odoo Integration Webhook Server")
        self.server = None
        self.host = "0.0.0.0"
        self.port = 8000
        self.is_server_running = False
        self.logger = logging.getLogger(__name__)
        
        self.event_received_handlers = []
        
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.post("/webhook/events")
        async def receive_event(event_data: WebhookEventModel):
            try:
                self.logger.debug(f"Received webhook event: {event_data.dict()}")
                
                # Convertir el modelo Pydantic a dict y mapear nombres de campos
                event_dict = {
                    'event_type': event_data.eventType,
                    'entity_type': event_data.entityType,
                    'event_id': event_data.eventId,
                    'timestamp': event_data.timeStamp,
                    'source_system': event_data.sourceSystem,
                    'payload': event_data.payload,
                    'context': event_data.context
                }
                
                integration_event = IntegrationEvent.from_dict(event_dict)
                
                # Llamar a los handlers registrados
                for handler in self.event_received_handlers:
                    try:
                        handler(integration_event)
                    except Exception as e:
                        self.logger.error(f"Error in event handler: {str(e)}")
                
                return JSONResponse(
                    status_code=200,
                    content={"success": True, "message": "Event processed successfully"}
                )
                
            except ValidationError as e:
                self.logger.error(f"Validation error in webhook: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid event data: {str(e)}")
            
            except Exception as e:
                self.logger.error(f"Error processing webhook event: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        @self.app.get("/webhook/health")
        async def health_check():
            return JSONResponse(
                status_code=200,
                content={"status": "healthy", "service": "Odoo Integration Webhook"}
            )
        
        @self.app.post("/webhook/test")
        async def test_endpoint():
            return JSONResponse(
                status_code=200,
                content={"message": "Webhook server is working correctly"}
            )
    
    async def start_server(self, host: str, port: int) -> None:
        try:
            self.host = host
            self.port = port
            
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
            self.server = uvicorn.Server(config)
            self.is_server_running = True
            
            self.logger.info(f"Starting webhook server on {host}:{port}")
            
            # Ejecutar el servidor de forma asíncrona
            await self.server.serve()
            
        except Exception as e:
            self.logger.error(f"Failed to start webhook server: {str(e)}")
            self.is_server_running = False
            raise
    
    async def stop_server(self) -> None:
        try:
            if self.server and self.is_server_running:
                self.logger.info("Stopping webhook server")
                self.server.should_exit = True
                self.is_server_running = False
                
                # Esperar un poco para que el servidor termine limpiamente
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error stopping webhook server: {str(e)}")
    
    def is_running(self) -> bool:
        return self.is_server_running
    
    def on_event_received(self, handler: Callable[[IntegrationEvent], None]) -> None:
        self.event_received_handlers.append(handler)
    
    def get_webhook_url(self) -> Optional[str]:
        if self.is_server_running:
            return f"http://{self.host}:{self.port}/webhook/events"
        return None
    
    async def health_check(self) -> bool:
        try:
            if not self.is_server_running:
                return False
            
            # Aquí podríamos hacer una llamada HTTP interna para verificar
            # Por simplicidad, solo verificamos el estado del servidor
            return self.server is not None and not self.server.should_exit
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False