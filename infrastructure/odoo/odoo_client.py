import logging
from typing import List, Optional, Dict, Any
import xmlrpc.client
from datetime import datetime

from ...domain.interfaces.odoo_repository import IOdooRepository
from ...domain.entities.odoo_record import OdooRecord, OdooSyncResult, OdooOperation


class OdooClientImpl(IOdooRepository):
    def __init__(self, url: str, database: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.database = database
        self.username = username
        self.password = password
        self.uid: Optional[int] = None
        self.logger = logging.getLogger(__name__)
        
        # Inicializar conexiones XML-RPC
        self.common = None
        self.models = None
        self._connected = False
    
    async def connect(self) -> bool:
        try:
            # Configurar conexiones XML-RPC
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            
            # Verificar versión de Odoo
            version = self.common.version()
            self.logger.info(f"Connecting to Odoo {version.get('server_version', 'Unknown')}")
            
            # Autenticar usuario
            self.uid = self.common.authenticate(self.database, self.username, self.password, {})
            
            if not self.uid:
                self.logger.error("Authentication failed - invalid credentials")
                return False
            
            self._connected = True
            self.logger.info(f"Successfully connected to Odoo as user ID: {self.uid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Odoo: {str(e)}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        self._connected = False
        self.uid = None
        self.common = None
        self.models = None
        self.logger.info("Disconnected from Odoo")
    
    async def is_connected(self) -> bool:
        if not self._connected or not self.uid:
            return False
        
        try:
            # Verificar conexión haciendo una llamada simple
            self.models.execute_kw(
                self.database, self.uid, self.password,
                'res.users', 'check_access_rights',
                ['read'], {'raise_exception': False}
            )
            return True
        except Exception:
            self._connected = False
            return False
    
    async def create_record(self, model: str, values: Dict[str, Any]) -> OdooSyncResult:
        try:
            if not await self.is_connected():
                await self.connect()
            
            record_id = self.models.execute_kw(
                self.database, self.uid, self.password,
                model, 'create', [values]
            )
            
            self.logger.info(f"Created record in {model} with ID: {record_id}")
            
            return OdooSyncResult(
                success=True,
                record_id=record_id,
                message=f"Record created successfully in {model}"
            )
            
        except Exception as e:
            error_msg = f"Failed to create record in {model}: {str(e)}"
            self.logger.error(error_msg)
            
            return OdooSyncResult(
                success=False,
                message=error_msg,
                error_details={'exception': str(e), 'model': model, 'values': values}
            )
    
    async def update_record(self, model: str, record_id: int, values: Dict[str, Any]) -> OdooSyncResult:
        try:
            if not await self.is_connected():
                await self.connect()
            
            success = self.models.execute_kw(
                self.database, self.uid, self.password,
                model, 'write', [[record_id], values]
            )
            
            if success:
                self.logger.info(f"Updated record {record_id} in {model}")
                
                return OdooSyncResult(
                    success=True,
                    record_id=record_id,
                    message=f"Record {record_id} updated successfully in {model}"
                )
            else:
                error_msg = f"Failed to update record {record_id} in {model}"
                self.logger.error(error_msg)
                
                return OdooSyncResult(
                    success=False,
                    message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Failed to update record {record_id} in {model}: {str(e)}"
            self.logger.error(error_msg)
            
            return OdooSyncResult(
                success=False,
                message=error_msg,
                error_details={'exception': str(e), 'model': model, 'record_id': record_id, 'values': values}
            )
    
    async def delete_record(self, model: str, record_id: int) -> OdooSyncResult:
        try:
            if not await self.is_connected():
                await self.connect()
            
            success = self.models.execute_kw(
                self.database, self.uid, self.password,
                model, 'unlink', [[record_id]]
            )
            
            if success:
                self.logger.info(f"Deleted record {record_id} from {model}")
                
                return OdooSyncResult(
                    success=True,
                    record_id=record_id,
                    message=f"Record {record_id} deleted successfully from {model}"
                )
            else:
                error_msg = f"Failed to delete record {record_id} from {model}"
                self.logger.error(error_msg)
                
                return OdooSyncResult(
                    success=False,
                    message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Failed to delete record {record_id} from {model}: {str(e)}"
            self.logger.error(error_msg)
            
            return OdooSyncResult(
                success=False,
                message=error_msg,
                error_details={'exception': str(e), 'model': model, 'record_id': record_id}
            )
    
    async def search_records(self, model: str, domain: List[tuple], limit: int = 100) -> List[int]:
        try:
            if not await self.is_connected():
                await self.connect()
            
            record_ids = self.models.execute_kw(
                self.database, self.uid, self.password,
                model, 'search', [domain],
                {'limit': limit}
            )
            
            self.logger.debug(f"Found {len(record_ids)} records in {model} matching domain: {domain}")
            return record_ids
            
        except Exception as e:
            self.logger.error(f"Failed to search records in {model}: {str(e)}")
            return []
    
    async def read_records(self, model: str, record_ids: List[int], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        try:
            if not await self.is_connected():
                await self.connect()
            
            records = self.models.execute_kw(
                self.database, self.uid, self.password,
                model, 'read', [record_ids],
                {'fields': fields} if fields else {}
            )
            
            self.logger.debug(f"Read {len(records)} records from {model}")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to read records from {model}: {str(e)}")
            return []
    
    async def search_read(self, model: str, domain: List[tuple], fields: Optional[List[str]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            if not await self.is_connected():
                await self.connect()
            
            records = self.models.execute_kw(
                self.database, self.uid, self.password,
                model, 'search_read', [domain],
                {'fields': fields, 'limit': limit} if fields else {'limit': limit}
            )
            
            self.logger.debug(f"Search-read found {len(records)} records in {model}")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to search-read records in {model}: {str(e)}")
            return []
    
    async def execute_operation(self, operation: OdooOperation) -> OdooSyncResult:
        if operation.operation_type == 'create':
            return await self.create_record(operation.model, operation.values)
        elif operation.operation_type == 'write':
            if not operation.record_id:
                return OdooSyncResult(
                    success=False,
                    message="Record ID required for write operation"
                )
            return await self.update_record(operation.model, operation.record_id, operation.values)
        elif operation.operation_type == 'unlink':
            if not operation.record_id:
                return OdooSyncResult(
                    success=False,
                    message="Record ID required for unlink operation"
                )
            return await self.delete_record(operation.model, operation.record_id)
        else:
            return OdooSyncResult(
                success=False,
                message=f"Unsupported operation type: {operation.operation_type}"
            )
    
    async def get_external_id(self, model: str, record_id: int) -> Optional[str]:
        try:
            external_ids = await self.search_read(
                'ir.model.data',
                [('model', '=', model), ('res_id', '=', record_id)],
                fields=['complete_name'],
                limit=1
            )
            
            if external_ids:
                return external_ids[0]['complete_name']
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get external ID for {model}.{record_id}: {str(e)}")
            return None
    
    async def find_by_external_id(self, external_id: str) -> Optional[OdooRecord]:
        try:
            external_data = await self.search_read(
                'ir.model.data',
                [('complete_name', '=', external_id)],
                fields=['model', 'res_id'],
                limit=1
            )
            
            if external_data:
                data = external_data[0]
                return OdooRecord(
                    model=data['model'],
                    record_id=data['res_id'],
                    external_id=external_id
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find record by external ID {external_id}: {str(e)}")
            return None
    
    async def set_external_id(self, model: str, record_id: int, external_id: str) -> bool:
        try:
            # Separar módulo y nombre del external_id
            if '.' in external_id:
                module, name = external_id.split('.', 1)
            else:
                module = '__import__'
                name = external_id
            
            result = await self.create_record('ir.model.data', {
                'name': name,
                'module': module,
                'model': model,
                'res_id': record_id,
                'noupdate': True
            })
            
            return result.success
            
        except Exception as e:
            self.logger.error(f"Failed to set external ID {external_id} for {model}.{record_id}: {str(e)}")
            return False