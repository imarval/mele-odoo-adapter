import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ...domain.entities.integration_event import IntegrationEvent
from ...domain.services.integration_service import IntegrationService
from ...domain.interfaces.signalr_client import ISignalRClient
from ...domain.interfaces.webhook_client import IWebhookClient
from ...infrastructure.signalr.signalr_client_impl import SignalRClientImpl
from ...infrastructure.http.webhook_client import WebhookClientImpl
from ...infrastructure.odoo.odoo_client import OdooClientImpl
from ...infrastructure.persistence.event_repository_impl import EventRepositoryImpl
from ..handlers.event_handler import EventHandler
from ..handlers.sync_handler import SyncHandler


class IntegrationOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Clientes e infraestructura
        self.signalr_client: Optional[ISignalRClient] = None
        self.webhook_client: Optional[IWebhookClient] = None
        self.odoo_client: Optional[OdooClientImpl] = None
        self.event_repository: Optional[EventRepositoryImpl] = None
        
        # Servicios y handlers
        self.integration_service: Optional[IntegrationService] = None
        self.event_handler: Optional[EventHandler] = None
        self.sync_handler: Optional[SyncHandler] = None
        
        # Estado
        self.is_running = False
        self._tasks = []
    
    async def initialize(self) -> bool:
        """
        Inicializa todos los componentes del orquestador
        """
        try:
            self.logger.info("Initializing Integration Orchestrator")
            
            # Inicializar repositorio de eventos
            self.event_repository = EventRepositoryImpl(
                db_path=self.config.get('database', {}).get('path', 'integration_events.db')
            )
            
            # Inicializar cliente Odoo
            odoo_config = self.config.get('odoo', {})
            self.odoo_client = OdooClientImpl(
                url=odoo_config.get('url'),
                database=odoo_config.get('database'),
                username=odoo_config.get('username'),
                password=odoo_config.get('password')
            )
            
            # Conectar a Odoo
            if not await self.odoo_client.connect():
                self.logger.error("Failed to connect to Odoo")
                return False
            
            # Inicializar servicio de integración
            self.integration_service = IntegrationService(
                odoo_repository=self.odoo_client,
                event_repository=self.event_repository
            )
            
            # Inicializar handlers
            self.event_handler = EventHandler(self.integration_service)
            self.sync_handler = SyncHandler(self.integration_service)
            
            # Inicializar clientes de comunicación
            await self._initialize_communication_clients()
            
            self.logger.info("Integration Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Integration Orchestrator: {str(e)}")
            return False
    
    async def _initialize_communication_clients(self):
        """
        Inicializa los clientes de comunicación (SignalR y Webhook)
        """
        # Inicializar cliente SignalR si está configurado
        signalr_config = self.config.get('signalr')
        if signalr_config and signalr_config.get('enabled', False):
            self.signalr_client = SignalRClientImpl()
            self.signalr_client.on_event_received(self._handle_signalr_event)
            self.signalr_client.on_connection_error(self._handle_signalr_error)
            self.signalr_client.on_disconnected(self._handle_signalr_disconnected)
        
        # Inicializar cliente Webhook si está configurado
        webhook_config = self.config.get('webhook')
        if webhook_config and webhook_config.get('enabled', False):
            self.webhook_client = WebhookClientImpl()
            self.webhook_client.on_event_received(self._handle_webhook_event)
    
    async def start(self) -> None:
        """
        Inicia el orquestador de integración
        """
        if self.is_running:
            self.logger.warning("Integration Orchestrator is already running")
            return
        
        try:
            self.logger.info("Starting Integration Orchestrator")
            self.is_running = True
            
            # Inicializar si no se ha hecho
            if not self.integration_service:
                if not await self.initialize():
                    raise Exception("Failed to initialize orchestrator")
            
            # Iniciar procesamiento de eventos
            if self.event_handler:
                task = asyncio.create_task(self.event_handler.start_processing())
                self._tasks.append(task)
            
            # Conectar cliente SignalR
            if self.signalr_client:
                signalr_config = self.config.get('signalr', {})
                url = signalr_config.get('url')
                subscription_id = signalr_config.get('subscription_id')
                
                if url and subscription_id:
                    if await self.signalr_client.connect(url, subscription_id):
                        await self.signalr_client.start_listening()
                        self.logger.info("SignalR client connected and listening")
                    else:
                        self.logger.error("Failed to connect SignalR client")
            
            # Iniciar servidor webhook
            if self.webhook_client:
                webhook_config = self.config.get('webhook', {})
                host = webhook_config.get('host', '0.0.0.0')
                port = webhook_config.get('port', 8000)
                
                task = asyncio.create_task(self.webhook_client.start_server(host, port))
                self._tasks.append(task)
                self.logger.info(f"Webhook server started on {host}:{port}")
            
            # Procesar eventos pendientes
            if self.event_handler:
                await self.event_handler.process_pending_events()
            
            self.logger.info("Integration Orchestrator started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Integration Orchestrator: {str(e)}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """
        Detiene el orquestador de integración
        """
        if not self.is_running:
            self.logger.warning("Integration Orchestrator is not running")
            return
        
        try:
            self.logger.info("Stopping Integration Orchestrator")
            self.is_running = False
            
            # Detener procesamiento de eventos
            if self.event_handler:
                await self.event_handler.stop_processing()
            
            # Desconectar cliente SignalR
            if self.signalr_client:
                await self.signalr_client.stop_listening()
                await self.signalr_client.disconnect()
            
            # Detener servidor webhook
            if self.webhook_client:
                await self.webhook_client.stop_server()
            
            # Cancelar tareas en ejecución
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Esperar a que las tareas terminen
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            self._tasks.clear()
            
            # Desconectar de Odoo
            if self.odoo_client:
                await self.odoo_client.disconnect()
            
            self.logger.info("Integration Orchestrator stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping Integration Orchestrator: {str(e)}")
    
    def _handle_signalr_event(self, event: IntegrationEvent) -> None:
        """
        Maneja eventos recibidos via SignalR
        """
        self.logger.debug(f"Received SignalR event: {event.event_id}")
        
        if self.event_handler:
            asyncio.create_task(self.event_handler.queue_event(event))
    
    def _handle_webhook_event(self, event: IntegrationEvent) -> None:
        """
        Maneja eventos recibidos via Webhook
        """
        self.logger.debug(f"Received Webhook event: {event.event_id}")
        
        if self.event_handler:
            asyncio.create_task(self.event_handler.queue_event(event))
    
    def _handle_signalr_error(self, error: str) -> None:
        """
        Maneja errores de conexión SignalR
        """
        self.logger.error(f"SignalR connection error: {error}")
    
    def _handle_signalr_disconnected(self) -> None:
        """
        Maneja desconexión de SignalR
        """
        self.logger.warning("SignalR client disconnected")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del orquestador
        """
        status = {
            'is_running': self.is_running,
            'timestamp': datetime.now().isoformat(),
            'signalr_connected': False,
            'webhook_running': False,
            'odoo_connected': False,
            'queue_size': 0
        }
        
        if self.signalr_client:
            status['signalr_connected'] = await self.signalr_client.is_connected()
        
        if self.webhook_client:
            status['webhook_running'] = self.webhook_client.is_running()
        
        if self.odoo_client:
            status['odoo_connected'] = await self.odoo_client.is_connected()
        
        if self.event_handler:
            status['queue_size'] = self.event_handler.get_queue_size()
        
        return status
    
    async def run_forever(self) -> None:
        """
        Ejecuta el orquestador indefinidamente
        """
        await self.start()
        
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, stopping...")
        finally:
            await self.stop()