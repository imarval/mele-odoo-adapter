# Odoo Integration Adapter

Cliente de integración Python para conectar IntegrationBridge con Odoo 18+. Implementa arquitectura clean y soporta comunicación via SignalR y webhooks HTTP.

## Características

- **Arquitectura Clean**: Separación clara entre dominio, aplicación e infraestructura
- **Comunicación Dual**: Soporte para SignalR (tiempo real) y webhooks HTTP
- **Cliente Odoo Nativo**: Integración directa con XML-RPC de Odoo
- **Persistencia Local**: SQLite para almacenamiento de eventos
- **Mapeo Flexible**: Configuración personalizable de entidades y campos
- **Manejo de Errores**: Sistema robusto de reintentos y logging
- **Monitoreo**: Endpoints de salud y métricas

## Arquitectura

```
OdooAdapter/
├── domain/                    # Entidades y reglas de negocio
│   ├── entities/
│   │   ├── integration_event.py
│   │   └── odoo_record.py
│   ├── interfaces/
│   │   ├── event_repository.py
│   │   ├── odoo_repository.py
│   │   ├── signalr_client.py
│   │   └── webhook_client.py
│   └── services/
│       └── integration_service.py
├── infrastructure/           # Implementaciones concretas
│   ├── signalr/
│   │   └── signalr_client_impl.py
│   ├── http/
│   │   └── webhook_client.py
│   ├── odoo/
│   │   └── odoo_client.py
│   └── persistence/
│       └── event_repository_impl.py
├── application/             # Casos de uso
│   ├── handlers/
│   │   ├── event_handler.py
│   │   └── sync_handler.py
│   └── services/
│       └── orchestrator.py
├── config/                # Configuración
│   ├── settings.py
│   └── odoo_config.py
└── main.py               # Punto de entrada
```

## Instalación

1. **Clonar el repositorio**:
```bash
git clone <repository-url>
cd IntegrationBridge/OdooAdapter
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\\Scripts\\activate  # Windows
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

## Configuración

### Archivo de Configuración

Editar `config.yaml`:

```yaml
# Configuración de Odoo
odoo:
  url: "http://localhost:8069"
  database: "odoo_db"
  username: "admin"
  password: "admin"

# Configuración de SignalR
signalr:
  enabled: true
  url: "http://localhost:5000/hubs/outbound-events"
  subscription_id: "your_subscription_id"

# Configuración de Webhook
webhook:
  enabled: true
  host: "0.0.0.0"
  port: 8000
```

### Variables de Entorno

Las variables de entorno sobrescriben la configuración del archivo:

```bash
export ODOO_URL="http://odoo.example.com:8069"
export ODOO_DATABASE="production_db"
export ODOO_USERNAME="integration_user"
export ODOO_PASSWORD="secure_password"
export SIGNALR_URL="http://integration-bridge.example.com/hubs/outbound-events"
export SIGNALR_SUBSCRIPTION_ID="tenant_123"
export WEBHOOK_HOST="0.0.0.0"
export WEBHOOK_PORT="8000"
```

## Uso

### Ejecución Básica

```bash
python main.py
```

### Ejecución con Configuración Específica

```bash
python main.py --config production.yaml
```

### Modo Desarrollo

```bash
python main.py --log-level DEBUG
```

## Funcionalidades

### 1. Recepción de Eventos

El adapter puede recibir eventos de dos formas:

#### SignalR (Tiempo Real)
- Conexión persistente al hub de IntegrationBridge
- Recepción automática de eventos
- Reconexión automática en caso de desconexión

#### Webhook HTTP
- Servidor HTTP que expone endpoint `/webhook/events`
- Recepción de eventos via POST
- Validación de estructura de datos

### 2. Procesamiento de Eventos

Los eventos se procesan según su tipo:

- **CREATE**: Crear nuevo registro en Odoo
- **UPDATE**: Actualizar registro existente
- **DELETE**: Eliminar registro
- **SYNC**: Sincronizar (crear o actualizar)

### 3. Mapeo de Entidades

El sistema mapea automáticamente entidades de IntegrationBridge a modelos de Odoo:

- **Product** → `product.template`
- **User** → `res.users`
- **Store** → `res.company`
- **Invoice** → `account.move`

### 4. Persistencia

Los eventos se almacenan localmente en SQLite para:

- Auditoría y trazabilidad
- Reintento de eventos fallidos
- Procesamiento offline

## API

### Endpoints de Webhook

#### Recibir Evento
```
POST /webhook/events
Content-Type: application/json

{
  "eventType": "Create",
  "entityType": "Product",
  "eventId": "evt_123",
  "timeStamp": "2024-01-01T00:00:00Z",
  "payload": {
    "data": {
      "name": "Nuevo Producto",
      "price": 100.0
    }
  }
}
```

#### Health Check
```
GET /webhook/health
```

#### Estado del Sistema
```
GET /status
```

## Mapeo de Campos

### Productos

| IntegrationBridge | Odoo | Tipo |
|-------------------|------|------|
| name | name | char |
| description | description | text |
| price | list_price | float |
| cost | standard_price | float |
| barcode | barcode | char |
| sku | default_code | char |

### Usuarios

| IntegrationBridge | Odoo | Tipo |
|-------------------|------|------|
| name | name | char |
| email | login | char |
| phone | phone | char |
| active | active | boolean |

## Logging

El sistema genera logs detallados con niveles configurables:

- **DEBUG**: Información detallada de desarrollo
- **INFO**: Eventos normales de operación
- **WARNING**: Situaciones anómalas no críticas
- **ERROR**: Errores que requieren atención
- **CRITICAL**: Errores críticos del sistema

## Monitoreo

### Métricas Disponibles

- Eventos procesados exitosamente
- Eventos fallidos
- Tiempo de procesamiento promedio
- Estado de conexiones (SignalR, Odoo)
- Tamaño de cola de eventos

### Health Checks

El sistema expone endpoints para verificar salud:

- `/webhook/health`: Estado del servidor webhook
- `/status`: Estado completo del sistema

## Desarrollo

### Ejecutar Tests

```bash
pytest
```

### Formatear Código

```bash
black .
isort .
```

### Linter

```bash
flake8 .
```

### Estructura de Tests

```bash
tests/
├── unit/
│   ├── test_domain/
│   ├── test_infrastructure/
│   └── test_application/
├── integration/
└── fixtures/
```

## Despliegue

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  odoo-adapter:
    build: .
    environment:
      - ODOO_URL=http://odoo:8069
      - ODOO_DATABASE=odoo
      - SIGNALR_URL=http://integration-bridge:5000/hubs/outbound-events
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
```

### Systemd Service

```ini
[Unit]
Description=Odoo Integration Adapter
After=network.target

[Service]
Type=simple
User=odoo-adapter
WorkingDirectory=/opt/odoo-adapter
ExecStart=/opt/odoo-adapter/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Resolución de Problemas

### Problemas Comunes

1. **Error de Conexión a Odoo**
   - Verificar URL, credenciales y conectividad de red
   - Verificar que el usuario tenga permisos necesarios

2. **Fallos de SignalR**
   - Verificar URL del hub y subscription ID
   - Revisar logs de IntegrationBridge

3. **Eventos no Procesados**
   - Verificar logs para errores de mapeo
   - Validar estructura de datos en eventos

### Logs de Depuración

```bash
# Habilitar debug logging
export LOG_LEVEL=DEBUG
python main.py
```

### Reiniciar Eventos Fallidos

```python
from application.handlers.sync_handler import SyncHandler
handler = SyncHandler(integration_service)
await handler.handle_retry_failed_events()
```

## Contribución

1. Fork el repositorio
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia
MIT License - ver archivo [LICENSE](LICENSE) para detalles.
