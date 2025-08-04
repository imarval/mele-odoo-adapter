from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class EventType(Enum):
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"
    SYNC = "Sync"


class EntityType(Enum):
    PRODUCT = "Product"
    USER = "User"
    STORE = "Store"
    INVOICE = "Invoice"
    SHIFT = "Shift"
    ZETA_REPORT = "ZetaReport"


@dataclass
class SourceSystem:
    erp_name: str
    instance_id: str


@dataclass
class MetaData:
    version: Optional[str] = None
    schema_version: Optional[str] = None


@dataclass
class Payload:
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[MetaData] = None


@dataclass
class Header:
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class Context:
    header: Optional[Header] = None
    retry_count: int = 0


@dataclass
class IntegrationEvent:
    event_type: EventType
    entity_type: EntityType
    event_id: str
    timestamp: datetime
    source_system: Optional[SourceSystem] = None
    payload: Optional[Payload] = None
    context: Optional[Context] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegrationEvent':
        return cls(
            event_type=EventType(data['event_type']),
            entity_type=EntityType(data['entity_type']),
            event_id=data['event_id'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            source_system=SourceSystem(**data['source_system']) if data.get('source_system') else None,
            payload=Payload(
                data=data['payload'].get('data') if data.get('payload') else None,
                metadata=MetaData(**data['payload']['metadata']) if data.get('payload', {}).get('metadata') else None
            ) if data.get('payload') else None,
            context=Context(
                header=Header(**data['context']['header']) if data.get('context', {}).get('header') else None,
                retry_count=data['context'].get('retry_count', 0) if data.get('context') else 0
            ) if data.get('context') else None
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'event_type': self.event_type.value,
            'entity_type': self.entity_type.value,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat()
        }
        
        if self.source_system:
            result['source_system'] = {
                'erp_name': self.source_system.erp_name,
                'instance_id': self.source_system.instance_id
            }
        
        if self.payload:
            result['payload'] = {'data': self.payload.data}
            if self.payload.metadata:
                result['payload']['metadata'] = {
                    'version': self.payload.metadata.version,
                    'schema_version': self.payload.metadata.schema_version
                }
        
        if self.context:
            result['context'] = {'retry_count': self.context.retry_count}
            if self.context.header:
                result['context']['header'] = {
                    'correlation_id': self.context.header.correlation_id,
                    'tenant_id': self.context.header.tenant_id,
                    'user_id': self.context.header.user_id
                }
        
        return result