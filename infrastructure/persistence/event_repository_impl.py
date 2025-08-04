import sqlite3
import json
import logging
from typing import List, Optional
from datetime import datetime
import aiosqlite

from ...domain.interfaces.event_repository import IEventRepository
from ...domain.entities.integration_event import IntegrationEvent


class EventRepositoryImpl(IEventRepository):
    def __init__(self, db_path: str = "integration_events.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._initialized = False
    
    async def _ensure_initialized(self):
        if not self._initialized:
            await self._initialize_database()
            self._initialized = True
    
    async def _initialize_database(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS integration_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        event_type TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source_system TEXT,
                        payload TEXT,
                        context TEXT,
                        status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_event_id ON integration_events(event_id)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_entity_type ON integration_events(entity_type)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status ON integration_events(status)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON integration_events(timestamp)
                """)
                
                await db.commit()
                
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def save_event(self, event: IntegrationEvent) -> bool:
        try:
            await self._ensure_initialized()
            
            now = datetime.now().isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO integration_events 
                    (event_id, event_type, entity_type, timestamp, source_system, payload, context, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.event_type.value,
                    event.entity_type.value,
                    event.timestamp.isoformat(),
                    json.dumps(event.source_system.__dict__) if event.source_system else None,
                    json.dumps(event.payload.__dict__) if event.payload else None,
                    json.dumps(event.context.__dict__) if event.context else None,
                    'pending',
                    now,
                    now
                ))
                
                await db.commit()
                
            self.logger.debug(f"Saved event {event.event_id} to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save event {event.event_id}: {str(e)}")
            return False
    
    async def get_event_by_id(self, event_id: str) -> Optional[IntegrationEvent]:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM integration_events WHERE event_id = ?
                """, (event_id,))
                
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_event(row)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get event {event_id}: {str(e)}")
            return None
    
    async def get_events_by_entity_type(self, entity_type: str, limit: int = 100) -> List[IntegrationEvent]:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM integration_events 
                    WHERE entity_type = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (entity_type, limit))
                
                rows = await cursor.fetchall()
                
                return [self._row_to_event(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get events by entity type {entity_type}: {str(e)}")
            return []
    
    async def get_pending_events(self, limit: int = 100) -> List[IntegrationEvent]:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM integration_events 
                    WHERE status = 'pending' 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                """, (limit,))
                
                rows = await cursor.fetchall()
                
                return [self._row_to_event(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get pending events: {str(e)}")
            return []
    
    async def mark_event_as_processed(self, event_id: str) -> bool:
        return await self._update_event_status(event_id, 'processed')
    
    async def mark_event_as_failed(self, event_id: str, error_message: str) -> bool:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE integration_events 
                    SET status = 'failed', error_message = ?, updated_at = ?
                    WHERE event_id = ?
                """, ('failed', error_message, datetime.now().isoformat(), event_id))
                
                await db.commit()
                
            self.logger.debug(f"Marked event {event_id} as failed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark event {event_id} as failed: {str(e)}")
            return False
    
    async def get_failed_events(self, limit: int = 100) -> List[IntegrationEvent]:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM integration_events 
                    WHERE status = 'failed' 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = await cursor.fetchall()
                
                return [self._row_to_event(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get failed events: {str(e)}")
            return []
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM integration_events 
                    WHERE timestamp < ? AND status = 'processed'
                """, (older_than.isoformat(),))
                
                await db.commit()
                
                deleted_count = cursor.rowcount
                self.logger.info(f"Cleaned up {deleted_count} old events")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old events: {str(e)}")
            return 0
    
    async def _update_event_status(self, event_id: str, status: str) -> bool:
        try:
            await self._ensure_initialized()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE integration_events 
                    SET status = ?, updated_at = ?
                    WHERE event_id = ?
                """, (status, datetime.now().isoformat(), event_id))
                
                await db.commit()
                
            self.logger.debug(f"Updated event {event_id} status to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update event {event_id} status: {str(e)}")
            return False
    
    def _row_to_event(self, row) -> IntegrationEvent:
        from ...domain.entities.integration_event import EventType, EntityType, SourceSystem, Payload, Context
        
        source_system = None
        if row['source_system']:
            source_data = json.loads(row['source_system'])
            source_system = SourceSystem(**source_data)
        
        payload = None
        if row['payload']:
            payload_data = json.loads(row['payload'])
            payload = Payload(**payload_data)
        
        context = None
        if row['context']:
            context_data = json.loads(row['context'])
            context = Context(**context_data)
        
        return IntegrationEvent(
            event_type=EventType(row['event_type']),
            entity_type=EntityType(row['entity_type']),
            event_id=row['event_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            source_system=source_system,
            payload=payload,
            context=context
        )