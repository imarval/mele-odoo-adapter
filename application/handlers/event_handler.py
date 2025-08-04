import asyncio
import logging
from typing import List

from ...domain.entities.integration_event import IntegrationEvent
from ...domain.services.integration_service import IntegrationService


class EventHandler:
    def __init__(self, integration_service: IntegrationService):
        self.integration_service = integration_service
        self.logger = logging.getLogger(__name__)
        self._processing_queue = asyncio.Queue()
        self._is_processing = False
    
    async def handle_event(self, event: IntegrationEvent) -> None:
        """
        Maneja un evento de integración individual
        """
        try:
            self.logger.info(f"Handling event {event.event_id} - {event.event_type.value} {event.entity_type.value}")
            
            result = await self.integration_service.process_integration_event(event)
            
            if result.success:
                self.logger.info(f"Successfully handled event {event.event_id}")
            else:
                self.logger.error(f"Failed to handle event {event.event_id}: {result.message}")
            
        except Exception as e:
            self.logger.error(f"Error handling event {event.event_id}: {str(e)}")
    
    async def queue_event(self, event: IntegrationEvent) -> None:
        """
        Añade un evento a la cola de procesamiento
        """
        await self._processing_queue.put(event)
        self.logger.debug(f"Queued event {event.event_id} for processing")
    
    async def start_processing(self) -> None:
        """
        Inicia el procesamiento de eventos en cola
        """
        if self._is_processing:
            self.logger.warning("Event processing is already running")
            return
        
        self._is_processing = True
        self.logger.info("Started event processing")
        
        while self._is_processing:
            try:
                # Esperar por un evento con timeout
                event = await asyncio.wait_for(self._processing_queue.get(), timeout=1.0)
                
                # Procesar el evento
                await self.handle_event(event)
                
                # Marcar la tarea como completada
                self._processing_queue.task_done()
                
            except asyncio.TimeoutError:
                # Timeout normal, continuar el loop
                continue
            except Exception as e:
                self.logger.error(f"Error in event processing loop: {str(e)}")
                await asyncio.sleep(1)  # Esperar antes de continuar
    
    async def stop_processing(self) -> None:
        """
        Detiene el procesamiento de eventos
        """
        self._is_processing = False
        self.logger.info("Stopped event processing")
        
        # Esperar a que se procesen los eventos pendientes
        await self._processing_queue.join()
    
    async def process_pending_events(self) -> int:
        """
        Procesa eventos pendientes desde el repositorio
        """
        from ...infrastructure.persistence.event_repository_impl import EventRepositoryImpl
        
        event_repo = EventRepositoryImpl()
        pending_events = await event_repo.get_pending_events(limit=100)
        
        processed_count = 0
        for event in pending_events:
            try:
                await self.handle_event(event)
                processed_count += 1
            except Exception as e:
                self.logger.error(f"Failed to process pending event {event.event_id}: {str(e)}")
        
        self.logger.info(f"Processed {processed_count} pending events")
        return processed_count
    
    async def handle_batch_events(self, events: List[IntegrationEvent]) -> None:
        """
        Maneja un lote de eventos de integración
        """
        self.logger.info(f"Handling batch of {len(events)} events")
        
        tasks = []
        for event in events:
            task = asyncio.create_task(self.handle_event(event))
            tasks.append(task)
        
        # Esperar a que se completen todos los eventos
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if not isinstance(result, Exception))
        error_count = len(results) - success_count
        
        self.logger.info(f"Batch processing complete: {success_count} success, {error_count} errors")
    
    def get_queue_size(self) -> int:
        """
        Obtiene el tamaño actual de la cola de procesamiento
        """
        return self._processing_queue.qsize()
    
    def is_processing(self) -> bool:
        """
        Verifica si el handler está procesando eventos
        """
        return self._is_processing