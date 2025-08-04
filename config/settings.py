import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path


class Settings:
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.yaml"
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """
        Carga la configuración desde archivo y variables de entorno
        """
        # Cargar desde archivo si existe
        config_path = Path(self.config_file)
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                    self._config = yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    self._config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        
        # Sobrescribir con variables de entorno
        self._load_env_variables()
    
    def _load_env_variables(self):
        """
        Carga configuración desde variables de entorno
        """
        # Configuración de Odoo
        if 'odoo' not in self._config:
            self._config['odoo'] = {}
        
        if os.getenv('ODOO_URL'):
            self._config['odoo']['url'] = os.getenv('ODOO_URL')
        if os.getenv('ODOO_DATABASE'):
            self._config['odoo']['database'] = os.getenv('ODOO_DATABASE')
        if os.getenv('ODOO_USERNAME'):
            self._config['odoo']['username'] = os.getenv('ODOO_USERNAME')
        if os.getenv('ODOO_PASSWORD'):
            self._config['odoo']['password'] = os.getenv('ODOO_PASSWORD')
        
        # Configuración de SignalR
        if 'signalr' not in self._config:
            self._config['signalr'] = {}
        
        if os.getenv('SIGNALR_URL'):
            self._config['signalr']['url'] = os.getenv('SIGNALR_URL')
        if os.getenv('SIGNALR_SUBSCRIPTION_ID'):
            self._config['signalr']['subscription_id'] = os.getenv('SIGNALR_SUBSCRIPTION_ID')
        if os.getenv('SIGNALR_ENABLED'):
            self._config['signalr']['enabled'] = os.getenv('SIGNALR_ENABLED').lower() == 'true'
        
        # Configuración de Webhook
        if 'webhook' not in self._config:
            self._config['webhook'] = {}
        
        if os.getenv('WEBHOOK_HOST'):
            self._config['webhook']['host'] = os.getenv('WEBHOOK_HOST')
        if os.getenv('WEBHOOK_PORT'):
            self._config['webhook']['port'] = int(os.getenv('WEBHOOK_PORT'))
        if os.getenv('WEBHOOK_ENABLED'):
            self._config['webhook']['enabled'] = os.getenv('WEBHOOK_ENABLED').lower() == 'true'
        
        # Configuración de base de datos
        if 'database' not in self._config:
            self._config['database'] = {}
        
        if os.getenv('DATABASE_PATH'):
            self._config['database']['path'] = os.getenv('DATABASE_PATH')
        
        # Configuración de logging
        if 'logging' not in self._config:
            self._config['logging'] = {}
        
        if os.getenv('LOG_LEVEL'):
            self._config['logging']['level'] = os.getenv('LOG_LEVEL')
        if os.getenv('LOG_FILE'):
            self._config['logging']['file'] = os.getenv('LOG_FILE')
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando notación de punto
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_odoo_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración completa de Odoo
        """
        return self._config.get('odoo', {})
    
    def get_signalr_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración completa de SignalR
        """
        return self._config.get('signalr', {})
    
    def get_webhook_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración completa de Webhook
        """
        return self._config.get('webhook', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración completa de base de datos
        """
        return self._config.get('database', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración completa de logging
        """
        return self._config.get('logging', {})
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Obtiene toda la configuración
        """
        return self._config.copy()
    
    def validate_required_config(self) -> bool:
        """
        Valida que la configuración requerida esté presente
        """
        errors = []
        
        # Validar configuración de Odoo
        odoo_config = self.get_odoo_config()
        required_odoo = ['url', 'database', 'username', 'password']
        
        for field in required_odoo:
            if not odoo_config.get(field):
                errors.append(f"Missing required Odoo configuration: {field}")
        
        # Validar configuración de SignalR (si está habilitado)
        signalr_config = self.get_signalr_config()
        if signalr_config.get('enabled', False):
            required_signalr = ['url', 'subscription_id']
            for field in required_signalr:
                if not signalr_config.get(field):
                    errors.append(f"Missing required SignalR configuration: {field}")
        
        # Validar configuración de Webhook (si está habilitado)
        webhook_config = self.get_webhook_config()
        if webhook_config.get('enabled', False):
            if not webhook_config.get('port'):
                errors.append("Missing required Webhook configuration: port")
        
        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False
        
        return True


# Configuración por defecto
DEFAULT_CONFIG = {
    'odoo': {
        'url': 'http://localhost:8069',
        'database': 'odoo',
        'username': 'admin',
        'password': 'admin'
    },
    'signalr': {
        'enabled': True,
        'url': 'http://localhost:5000/hubs/outbound-events',
        'subscription_id': 'default'
    },
    'webhook': {
        'enabled': True,
        'host': '0.0.0.0',
        'port': 8000
    },
    'database': {
        'path': 'integration_events.db'
    },
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': None
    },
    'sync': {
        'batch_size': 100,
        'retry_attempts': 3,
        'retry_delay': 5
    }
}