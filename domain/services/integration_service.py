from typing import Dict, Any, List
import logging
from datetime import datetime

from ..entities.integration_event import IntegrationEvent, EntityType, EventType
from ..entities.odoo_record import OdooRecord, OdooSyncResult, OdooOperation
from ..interfaces.odoo_repository import IOdooRepository
from ..interfaces.event_repository import IEventRepository


class IntegrationService:
    def __init__(self, odoo_repository: IOdooRepository, event_repository: IEventRepository):
        self.odoo_repository = odoo_repository
        self.event_repository = event_repository
        self.logger = logging.getLogger(__name__)
        
        # Mapeo de EntityType a modelo Odoo
        self.entity_model_mapping = {
            EntityType.PRODUCT: 'product.template',
            EntityType.USER: 'res.users',
            EntityType.STORE: 'res.company',
            EntityType.INVOICE: 'account.move',
            EntityType.SHIFT: 'hr.attendance',
            EntityType.ZETA_REPORT: 'account.report'
        }
    
    async def process_integration_event(self, event: IntegrationEvent) -> OdooSyncResult:
        try:
            await self.event_repository.save_event(event)
            
            if not await self.odoo_repository.is_connected():
                await self.odoo_repository.connect()
            
            result = await self._handle_event_by_type(event)
            
            if result.success:
                await self.event_repository.mark_event_as_processed(event.event_id)
                self.logger.info(f"Successfully processed event {event.event_id}")
            else:
                await self.event_repository.mark_event_as_failed(event.event_id, result.message or "Unknown error")
                self.logger.error(f"Failed to process event {event.event_id}: {result.message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing event {event.event_id}: {str(e)}"
            self.logger.error(error_msg)
            await self.event_repository.mark_event_as_failed(event.event_id, error_msg)
            
            return OdooSyncResult(
                success=False,
                message=error_msg,
                error_details={'exception': str(e)}
            )
    
    async def _handle_event_by_type(self, event: IntegrationEvent) -> OdooSyncResult:
        model = self.entity_model_mapping.get(event.entity_type)
        if not model:
            return OdooSyncResult(
                success=False,
                message=f"Unsupported entity type: {event.entity_type.value}"
            )
        
        payload_data = event.payload.data if event.payload else {}
        
        if event.event_type == EventType.CREATE:
            return await self._handle_create_event(model, payload_data, event)
        elif event.event_type == EventType.UPDATE:
            return await self._handle_update_event(model, payload_data, event)
        elif event.event_type == EventType.DELETE:
            return await self._handle_delete_event(model, payload_data, event)
        elif event.event_type == EventType.SYNC:
            return await self._handle_sync_event(model, payload_data, event)
        else:
            return OdooSyncResult(
                success=False,
                message=f"Unsupported event type: {event.event_type.value}"
            )
    
    async def _handle_create_event(self, model: str, data: Dict[str, Any], event: IntegrationEvent) -> OdooSyncResult:
        mapped_values = await self._map_values_to_odoo(model, data, event.entity_type)
        
        result = await self.odoo_repository.create_record(model, mapped_values)
        
        if result.success and result.record_id:
            external_id = f"{event.source_system.erp_name}_{event.source_system.instance_id}_{data.get('id', event.event_id)}"
            await self.odoo_repository.set_external_id(model, result.record_id, external_id)
        
        return result
    
    async def _handle_update_event(self, model: str, data: Dict[str, Any], event: IntegrationEvent) -> OdooSyncResult:
        external_id = f"{event.source_system.erp_name}_{event.source_system.instance_id}_{data.get('id')}"
        existing_record = await self.odoo_repository.find_by_external_id(external_id)
        
        if not existing_record or not existing_record.record_id:
            return OdooSyncResult(
                success=False,
                message=f"Record not found with external_id: {external_id}"
            )
        
        mapped_values = await self._map_values_to_odoo(model, data, event.entity_type)
        
        return await self.odoo_repository.update_record(model, existing_record.record_id, mapped_values)
    
    async def _handle_delete_event(self, model: str, data: Dict[str, Any], event: IntegrationEvent) -> OdooSyncResult:
        external_id = f"{event.source_system.erp_name}_{event.source_system.instance_id}_{data.get('id')}"
        existing_record = await self.odoo_repository.find_by_external_id(external_id)
        
        if not existing_record or not existing_record.record_id:
            return OdooSyncResult(
                success=False,
                message=f"Record not found with external_id: {external_id}"
            )
        
        return await self.odoo_repository.delete_record(model, existing_record.record_id)
    
    async def _handle_sync_event(self, model: str, data: Dict[str, Any], event: IntegrationEvent) -> OdooSyncResult:
        external_id = f"{event.source_system.erp_name}_{event.source_system.instance_id}_{data.get('id')}"
        existing_record = await self.odoo_repository.find_by_external_id(external_id)
        
        mapped_values = await self._map_values_to_odoo(model, data, event.entity_type)
        
        if existing_record and existing_record.record_id:
            return await self.odoo_repository.update_record(model, existing_record.record_id, mapped_values)
        else:
            result = await self.odoo_repository.create_record(model, mapped_values)
            if result.success and result.record_id:
                await self.odoo_repository.set_external_id(model, result.record_id, external_id)
            return result
    
    async def _map_values_to_odoo(self, model: str, data: Dict[str, Any], entity_type: EntityType) -> Dict[str, Any]:
        if entity_type == EntityType.PRODUCT:
            return await self._map_product_values(data)
        elif entity_type == EntityType.USER:
            return await self._map_user_values(data)
        elif entity_type == EntityType.STORE:
            return await self._map_store_values(data)
        elif entity_type == EntityType.INVOICE:
            return await self._map_invoice_values(data)
        else:
            return data
    
    async def _map_product_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {}
        
        if 'name' in data:
            mapped['name'] = data['name']
        if 'description' in data:
            mapped['description'] = data['description']
        if 'price' in data:
            mapped['list_price'] = float(data['price'])
        if 'cost' in data:
            mapped['standard_price'] = float(data['cost'])
        if 'barcode' in data:
            mapped['barcode'] = data['barcode']
        if 'category' in data:
            mapped['categ_id'] = await self._find_or_create_category(data['category'])
        if 'active' in data:
            mapped['active'] = data['active']
            
        return mapped
    
    async def _map_user_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {}
        
        if 'name' in data:
            mapped['name'] = data['name']
        if 'email' in data:
            mapped['login'] = data['email']
            mapped['email'] = data['email']
        if 'phone' in data:
            mapped['phone'] = data['phone']
        if 'active' in data:
            mapped['active'] = data['active']
            
        return mapped
    
    async def _map_store_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {}
        
        if 'name' in data:
            mapped['name'] = data['name']
        if 'address' in data:
            mapped['street'] = data['address']
        if 'phone' in data:
            mapped['phone'] = data['phone']
        if 'email' in data:
            mapped['email'] = data['email']
            
        return mapped
    
    async def _map_invoice_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        mapped = {}
        
        if 'partner_id' in data:
            mapped['partner_id'] = data['partner_id']
        if 'amount_total' in data:
            mapped['amount_total'] = float(data['amount_total'])
        if 'date' in data:
            mapped['invoice_date'] = data['date']
        if 'reference' in data:
            mapped['ref'] = data['reference']
            
        return mapped
    
    async def _find_or_create_category(self, category_name: str) -> int:
        domain = [('name', '=', category_name)]
        category_ids = await self.odoo_repository.search_records('product.category', domain, limit=1)
        
        if category_ids:
            return category_ids[0]
        
        result = await self.odoo_repository.create_record('product.category', {'name': category_name})
        return result.record_id if result.success else 1