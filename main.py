#!/usr/bin/env python3
"""
Cliente de Integración Odoo para IntegrationBridge
Punto de entrada principal de la aplicación
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from config.settings import Settings
from application.services.orchestrator import IntegrationOrchestrator


def setup_logging(config: dict):
    """
    Configura el sistema de logging
    """
    log_level = getattr(logging, config.get('level', 'INFO').upper())
    log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('file')
    
    logging_config = {
        'level': log_level,
        'format': log_format
    }
    
    if log_file:
        logging_config['filename'] = log_file
        logging_config['filemode'] = 'a'
    
    logging.basicConfig(**logging_config)
    
    # Configurar loggers específicos
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('signalrcore').setLevel(logging.WARNING)


async def main():
    """
    Función principal de la aplicación
    """
    # Cargar configuración
    settings = Settings()
    
    # Configurar logging
    setup_logging(settings.get_logging_config())
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Odoo Integration Adapter Starting")
    logger.info("=" * 60)
    
    # Validar configuración
    if not settings.validate_required_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Crear orquestador
    orchestrator = IntegrationOrchestrator(settings.get_all_config())
    
    # Configurar manejo de señales
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(orchestrator.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Inicializar y ejecutar
        if await orchestrator.initialize():
            logger.info("Orchestrator initialized successfully")
            
            # Mostrar configuración activa
            status = await orchestrator.get_status()
            logger.info(f"SignalR enabled: {settings.get('signalr.enabled', False)}")
            logger.info(f"Webhook enabled: {settings.get('webhook.enabled', False)}")
            logger.info(f"Odoo URL: {settings.get('odoo.url')}")
            logger.info(f"Database: {settings.get('database.path')}")
            
            # Ejecutar indefinidamente
            await orchestrator.run_forever()
        else:
            logger.error("Failed to initialize orchestrator")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        await orchestrator.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)