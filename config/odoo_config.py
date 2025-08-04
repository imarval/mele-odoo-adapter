from typing import Dict, Any, List
from dataclasses import dataclass
from ..domain.entities.integration_event import EntityType


@dataclass
class OdooModelMapping:
    """
    Mapeo entre EntityType y modelo de Odoo
    """
    entity_type: EntityType
    odoo_model: str
    key_field: str = 'id'  # Campo clave para identificar registros
    name_field: str = 'name'  # Campo de nombre/descripción
    active_field: str = 'active'  # Campo para activar/desactivar
    create_if_not_exists: bool = True


@dataclass
class FieldMapping:
    """
    Mapeo de campos entre IntegrationBridge y Odoo
    """
    source_field: str
    target_field: str
    field_type: str = 'char'  # char, integer, float, boolean, date, datetime, text
    required: bool = False
    default_value: Any = None
    transform_function: str = None  # Nombre de función de transformación


class OdooConfig:
    """
    Configuración específica para mapeos y reglas de Odoo
    """
    
    # Mapeo de entidades a modelos de Odoo
    MODEL_MAPPINGS = {
        EntityType.PRODUCT: OdooModelMapping(
            entity_type=EntityType.PRODUCT,
            odoo_model='product.template',
            key_field='default_code',  # SKU del producto
            name_field='name',
            active_field='active'
        ),
        EntityType.USER: OdooModelMapping(
            entity_type=EntityType.USER,
            odoo_model='res.users',
            key_field='login',
            name_field='name',
            active_field='active'
        ),
        EntityType.STORE: OdooModelMapping(
            entity_type=EntityType.STORE,
            odoo_model='res.company',
            key_field='vat',  # NIT o código tributario
            name_field='name',
            active_field='active'
        ),
        EntityType.INVOICE: OdooModelMapping(
            entity_type=EntityType.INVOICE,
            odoo_model='account.move',
            key_field='name',  # Número de factura
            name_field='name',
            create_if_not_exists=False  # Las facturas no se crean automáticamente
        )
    }
    
    # Mapeo de campos para productos
    PRODUCT_FIELD_MAPPINGS = [
        FieldMapping('name', 'name', 'char', required=True),
        FieldMapping('description', 'description', 'text'),
        FieldMapping('price', 'list_price', 'float'),
        FieldMapping('cost', 'standard_price', 'float'),
        FieldMapping('barcode', 'barcode', 'char'),
        FieldMapping('sku', 'default_code', 'char'),
        FieldMapping('active', 'active', 'boolean', default_value=True),
        FieldMapping('weight', 'weight', 'float'),
        FieldMapping('volume', 'volume', 'float'),
        FieldMapping('category', 'categ_id', 'many2one', transform_function='find_or_create_category')
    ]
    
    # Mapeo de campos para usuarios
    USER_FIELD_MAPPINGS = [
        FieldMapping('name', 'name', 'char', required=True),
        FieldMapping('email', 'login', 'char', required=True),
        FieldMapping('email', 'email', 'char'),
        FieldMapping('phone', 'phone', 'char'),
        FieldMapping('mobile', 'mobile', 'char'),
        FieldMapping('active', 'active', 'boolean', default_value=True),
        FieldMapping('is_admin', 'is_admin', 'boolean', default_value=False),
        FieldMapping('language', 'lang', 'char', default_value='es_ES'),
        FieldMapping('timezone', 'tz', 'char', default_value='America/Caracas')
    ]
    
    # Mapeo de campos para tiendas/compañías
    STORE_FIELD_MAPPINGS = [
        FieldMapping('name', 'name', 'char', required=True),
        FieldMapping('address', 'street', 'char'),
        FieldMapping('city', 'city', 'char'),
        FieldMapping('state', 'state_id', 'many2one', transform_function='find_state'),
        FieldMapping('country', 'country_id', 'many2one', transform_function='find_country'),
        FieldMapping('phone', 'phone', 'char'),
        FieldMapping('email', 'email', 'char'),
        FieldMapping('vat', 'vat', 'char'),
        FieldMapping('website', 'website', 'char'),
        FieldMapping('currency', 'currency_id', 'many2one', transform_function='find_currency')
    ]
    
    # Mapeo de campos para facturas
    INVOICE_FIELD_MAPPINGS = [
        FieldMapping('number', 'name', 'char'),
        FieldMapping('date', 'invoice_date', 'date'),
        FieldMapping('due_date', 'invoice_date_due', 'date'),
        FieldMapping('partner_id', 'partner_id', 'many2one', required=True),
        FieldMapping('amount_total', 'amount_total', 'float'),
        FieldMapping('amount_tax', 'amount_tax', 'float'),
        FieldMapping('amount_untaxed', 'amount_untaxed', 'float'),
        FieldMapping('state', 'state', 'selection'),
        FieldMapping('reference', 'ref', 'char'),
        FieldMapping('currency', 'currency_id', 'many2one', transform_function='find_currency')
    ]
    
    @classmethod
    def get_model_mapping(cls, entity_type: EntityType) -> OdooModelMapping:
        """
        Obtiene el mapeo de modelo para un tipo de entidad
        """
        return cls.MODEL_MAPPINGS.get(entity_type)
    
    @classmethod
    def get_field_mappings(cls, entity_type: EntityType) -> List[FieldMapping]:
        """
        Obtiene los mapeos de campos para un tipo de entidad
        """
        mapping_dict = {
            EntityType.PRODUCT: cls.PRODUCT_FIELD_MAPPINGS,
            EntityType.USER: cls.USER_FIELD_MAPPINGS,
            EntityType.STORE: cls.STORE_FIELD_MAPPINGS,
            EntityType.INVOICE: cls.INVOICE_FIELD_MAPPINGS
        }
        
        return mapping_dict.get(entity_type, [])
    
    @classmethod
    def get_required_fields(cls, entity_type: EntityType) -> List[str]:
        """
        Obtiene la lista de campos requeridos para un tipo de entidad
        """
        field_mappings = cls.get_field_mappings(entity_type)
        return [mapping.target_field for mapping in field_mappings if mapping.required]
    
    @classmethod
    def get_default_values(cls, entity_type: EntityType) -> Dict[str, Any]:
        """
        Obtiene los valores por defecto para un tipo de entidad
        """
        field_mappings = cls.get_field_mappings(entity_type)
        defaults = {}
        
        for mapping in field_mappings:
            if mapping.default_value is not None:
                defaults[mapping.target_field] = mapping.default_value
        
        return defaults
    
    @classmethod
    def should_create_if_not_exists(cls, entity_type: EntityType) -> bool:
        """
        Verifica si se debe crear el registro si no existe
        """
        model_mapping = cls.get_model_mapping(entity_type)
        return model_mapping.create_if_not_exists if model_mapping else True


# Configuración de transformaciones específicas
FIELD_TRANSFORMATIONS = {
    'find_or_create_category': {
        'model': 'product.category',
        'search_field': 'name',
        'create_values': {'name': '{value}'}
    },
    'find_state': {
        'model': 'res.country.state',
        'search_field': 'name',
        'domain_extra': [('country_id.code', '=', 'VE')]  # Ejemplo para Venezuela
    },
    'find_country': {
        'model': 'res.country',
        'search_field': 'code',
        'fallback_field': 'name'
    },
    'find_currency': {
        'model': 'res.currency',
        'search_field': 'name',
        'fallback_search': 'symbol'
    }
}


# Configuración de validaciones
VALIDATION_RULES = {
    EntityType.PRODUCT: {
        'name': {'min_length': 1, 'max_length': 255},
        'list_price': {'min_value': 0},
        'standard_price': {'min_value': 0},
        'barcode': {'pattern': r'^[0-9]{8,13}$'}  # Códigos de barras válidos
    },
    EntityType.USER: {
        'login': {'email_format': True},
        'email': {'email_format': True},
        'phone': {'pattern': r'^\+?[0-9\-\s\(\)]+$'}
    },
    EntityType.STORE: {
        'name': {'min_length': 1, 'max_length': 255},
        'vat': {'pattern': r'^[A-Z0-9\-]+$'},
        'email': {'email_format': True}
    }
}