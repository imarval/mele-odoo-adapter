import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ...domain.entities.integration_event import IntegrationEvent, EntityType
from ...domain.services.integration_service import IntegrationService


class SyncHandler:
    def __init__(self, integration_service: IntegrationService):
        self.integration_service = integration_service
        self.logger = logging.getLogger(__name__)
    
    async def handle_full_sync(self, entity_type: EntityType, data_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Maneja una sincronización completa de entidades
        """
        try:
            self.logger.info(f"Starting full sync for {entity_type.value} - {len(data_batch)} records")
            
            results = {
                'total': len(data_batch),
                'success': 0,
                'failed': 0,
                'errors': []
            }
            
            for data in data_batch:
                try:
                    # Crear evento de sincronización
                    sync_event = self._create_sync_event(entity_type, data)
                    
                    # Procesar el evento
                    result = await self.integration_service.process_integration_event(sync_event)
                    
                    if result.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'record_id': data.get('id'),
                            'error': result.message
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'record_id': data.get('id'),
                        'error': str(e)
                    })
            
            self.logger.info(f"Full sync completed for {entity_type.value}: {results['success']} success, {results['failed']} failed")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in full sync for {entity_type.value}: {str(e)}")
            return {
                'total': len(data_batch),
                'success': 0,
                'failed': len(data_batch),
                'errors': [{'error': str(e)}]
            }
    
    async def handle_incremental_sync(self, entity_type: EntityType, since: datetime) -> Dict[str, Any]:
        """
        Maneja una sincronización incremental desde una fecha específica
        """
        try:
            from ...infrastructure.persistence.event_repository_impl import EventRepositoryImpl
            
            self.logger.info(f"Starting incremental sync for {entity_type.value} since {since}")
            
            event_repo = EventRepositoryImpl()
            
            # Obtener eventos desde la fecha especificada
            all_events = await event_repo.get_events_by_entity_type(entity_type.value, limit=1000)
            recent_events = [
                event for event in all_events 
                if event.timestamp >= since
            ]
            
            results = {
                'total': len(recent_events),
                'success': 0,
                'failed': 0,
                'errors': []
            }
            
            for event in recent_events:
                try:
                    result = await self.integration_service.process_integration_event(event)
                    
                    if result.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'event_id': event.event_id,
                            'error': result.message
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'event_id': event.event_id,
                        'error': str(e)
                    })
            
            self.logger.info(f"Incremental sync completed for {entity_type.value}: {results['success']} success, {results['failed']} failed")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in incremental sync for {entity_type.value}: {str(e)}")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'errors': [{'error': str(e)}]
            }
    
    async def handle_retry_failed_events(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        Reintenta eventos fallidos
        """
        try:
            from ...infrastructure.persistence.event_repository_impl import EventRepositoryImpl
            
            self.logger.info("Starting retry of failed events")
            
            event_repo = EventRepositoryImpl()
            failed_events = await event_repo.get_failed_events(limit=100)
            
            results = {
                'total': len(failed_events),
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }
            
            for event in failed_events:
                try:
                    # Verificar si el evento ha excedido el número máximo de reintentos
                    retry_count = event.context.retry_count if event.context else 0
                    
                    if retry_count >= max_retries:
                        results['skipped'] += 1
                        continue
                    
                    # Incrementar contador de reintentos
                    if event.context:
                        event.context.retry_count += 1
                    
                    # Procesar el evento
                    result = await self.integration_service.process_integration_event(event)
                    
                    if result.success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'event_id': event.event_id,
                            'error': result.message
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'event_id': event.event_id,
                        'error': str(e)
                    })
            
            self.logger.info(f"Retry completed: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in retry failed events: {str(e)}")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'errors': [{'error': str(e)}]
            }
    
    async def cleanup_old_events(self, days_old: int = 30) -> int:
        """
        Limpia eventos antiguos del repositorio
        """
        try:
            from ...infrastructure.persistence.event_repository_impl import EventRepositoryImpl
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            event_repo = EventRepositoryImpl()
            
            deleted_count = await event_repo.cleanup_old_events(cutoff_date)
            
            self.logger.info(f"Cleaned up {deleted_count} events older than {days_old} days")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old events: {str(e)}")
            return 0
    
    def _create_sync_event(self, entity_type: EntityType, data: Dict[str, Any]) -> IntegrationEvent:
        """
        Crea un evento de sincronización a partir de datos
        """
        from ...domain.entities.integration_event import EventType, SourceSystem, Payload
        
        return IntegrationEvent(
            event_type=EventType.SYNC,
            entity_type=entity_type,
            event_id=f"sync_{entity_type.value}_{data.get('id', 'unknown')}_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            source_system=SourceSystem(
                erp_name="manual_sync",
                instance_id="odoo_adapter"
            ),
            payload=Payload(data=data)
        )