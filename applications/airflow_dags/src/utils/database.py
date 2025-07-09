"""
Database utilities for Airflow DAGs

Simple functions for database operations using Airflow PostgresHook.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from airflow.providers.postgres.hooks.postgres import PostgresHook

# Configure logging
logger = logging.getLogger(__name__)


# Database connection utilities
def get_postgres_hook() -> PostgresHook:
    """Get a PostgresHook instance for pxy6 database"""
    return PostgresHook(postgres_conn_id='pxy6_postgres')


def execute_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a query using Airflow PostgresHook"""
    hook = get_postgres_hook()
    return hook.get_records(query, parameters)


def execute_insert(query: str, parameters: Optional[Dict[str, Any]] = None) -> None:
    """Execute an insert/update query using Airflow PostgresHook"""
    hook = get_postgres_hook()
    hook.run(query, parameters)


# Shopify data upsert functions
def upsert_customer(customer_data: Dict[str, Any]):
    """Insert or update customer data"""
    
    query = """
    INSERT INTO customers (
        id, email, first_name, last_name, phone, created_at, updated_at,
        accepts_marketing, state, tags, total_spent_amount, total_spent_currency,
        number_of_orders, verified_email, tax_exempt, addresses, metafields,
        shopify_created_at, shopify_updated_at
    ) VALUES (
        %(id)s, %(email)s, %(first_name)s, %(last_name)s, %(phone)s, %(created_at)s, %(updated_at)s,
        %(accepts_marketing)s, %(state)s, %(tags)s, %(total_spent_amount)s, %(total_spent_currency)s,
        %(number_of_orders)s, %(verified_email)s, %(tax_exempt)s, %(addresses)s, %(metafields)s,
        %(shopify_created_at)s, %(shopify_updated_at)s
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        phone = EXCLUDED.phone,
        updated_at = EXCLUDED.updated_at,
        accepts_marketing = EXCLUDED.accepts_marketing,
        state = EXCLUDED.state,
        tags = EXCLUDED.tags,
        total_spent_amount = EXCLUDED.total_spent_amount,
        total_spent_currency = EXCLUDED.total_spent_currency,
        number_of_orders = EXCLUDED.number_of_orders,
        verified_email = EXCLUDED.verified_email,
        tax_exempt = EXCLUDED.tax_exempt,
        addresses = EXCLUDED.addresses,
        metafields = EXCLUDED.metafields,
        shopify_updated_at = EXCLUDED.shopify_updated_at,
        last_sync_at = CURRENT_TIMESTAMP
    """
    
    # Process customer data to extract fields
    total_spent = customer_data.get('totalSpentV2', {})
    
    params = {
        'id': int(customer_data['id'].split('/')[-1]),
        'email': customer_data.get('email'),
        'first_name': customer_data.get('firstName'),
        'last_name': customer_data.get('lastName'),
        'phone': customer_data.get('phone'),
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'accepts_marketing': customer_data.get('acceptsMarketing', False),
        'state': customer_data.get('state'),
        'tags': customer_data.get('tags'),
        'total_spent_amount': float(total_spent.get('amount', 0)) if total_spent.get('amount') else 0,
        'total_spent_currency': total_spent.get('currencyCode'),
        'number_of_orders': customer_data.get('numberOfOrders', 0),
        'verified_email': customer_data.get('verifiedEmail', False),
        'tax_exempt': customer_data.get('taxExempt', False),
        'addresses': json.dumps(customer_data.get('addresses', [])),
        'metafields': json.dumps(customer_data.get('metafields', {})),
        'shopify_created_at': customer_data.get('createdAt'),
        'shopify_updated_at': customer_data.get('updatedAt')
    }
    
    execute_insert(query, params)


def upsert_product(product_data: Dict[str, Any]):
    """Insert or update product data"""
    
    query = """
    INSERT INTO products (
        id, title, handle, description, description_html, product_type, vendor,
        tags, status, total_inventory, online_store_url, seo_title, seo_description,
        options, variants, images, metafields, collections, shopify_created_at,
        shopify_updated_at, published_at
    ) VALUES (
        %(id)s, %(title)s, %(handle)s, %(description)s, %(description_html)s, %(product_type)s, %(vendor)s,
        %(tags)s, %(status)s, %(total_inventory)s, %(online_store_url)s, %(seo_title)s, %(seo_description)s,
        %(options)s, %(variants)s, %(images)s, %(metafields)s, %(collections)s, %(shopify_created_at)s,
        %(shopify_updated_at)s, %(published_at)s
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        handle = EXCLUDED.handle,
        description = EXCLUDED.description,
        description_html = EXCLUDED.description_html,
        product_type = EXCLUDED.product_type,
        vendor = EXCLUDED.vendor,
        tags = EXCLUDED.tags,
        status = EXCLUDED.status,
        total_inventory = EXCLUDED.total_inventory,
        online_store_url = EXCLUDED.online_store_url,
        seo_title = EXCLUDED.seo_title,
        seo_description = EXCLUDED.seo_description,
        options = EXCLUDED.options,
        variants = EXCLUDED.variants,
        images = EXCLUDED.images,
        metafields = EXCLUDED.metafields,
        collections = EXCLUDED.collections,
        shopify_updated_at = EXCLUDED.shopify_updated_at,
        published_at = EXCLUDED.published_at,
        last_sync_at = CURRENT_TIMESTAMP
    """
    
    # Process product data
    seo = product_data.get('seo', {})
    
    params = {
        'id': int(product_data['id'].split('/')[-1]),
        'title': product_data.get('title'),
        'handle': product_data.get('handle'),
        'description': product_data.get('description'),
        'description_html': product_data.get('descriptionHtml'),
        'product_type': product_data.get('productType'),
        'vendor': product_data.get('vendor'),
        'tags': product_data.get('tags', []),
        'status': product_data.get('status'),
        'total_inventory': product_data.get('totalInventory'),
        'online_store_url': product_data.get('onlineStoreUrl'),
        'seo_title': seo.get('title'),
        'seo_description': seo.get('description'),
        'options': json.dumps(product_data.get('options', [])),
        'variants': json.dumps(product_data.get('variants', {})),
        'images': json.dumps(product_data.get('images', {})),
        'metafields': json.dumps(product_data.get('metafields', {})),
        'collections': json.dumps(product_data.get('collections', {})),
        'shopify_created_at': product_data.get('createdAt'),
        'shopify_updated_at': product_data.get('updatedAt'),
        'published_at': product_data.get('publishedAt')
    }
    
    execute_insert(query, params)


def upsert_order(order_data: Dict[str, Any]):
    """Insert or update order data"""
    
    query = """
    INSERT INTO orders (
        id, name, email, customer_id, total_price_amount, total_price_currency,
        subtotal_price_amount, subtotal_price_currency, total_tax_amount, total_tax_currency,
        total_shipping_amount, total_shipping_currency, financial_status, fulfillment_status,
        cancelled, cancel_reason, tags, note, line_items, shipping_address, billing_address,
        customer_journey, shopify_created_at, shopify_updated_at, processed_at, closed_at,
        cancelled_at
    ) VALUES (
        %(id)s, %(name)s, %(email)s, %(customer_id)s, %(total_price_amount)s, %(total_price_currency)s,
        %(subtotal_price_amount)s, %(subtotal_price_currency)s, %(total_tax_amount)s, %(total_tax_currency)s,
        %(total_shipping_amount)s, %(total_shipping_currency)s, %(financial_status)s, %(fulfillment_status)s,
        %(cancelled)s, %(cancel_reason)s, %(tags)s, %(note)s, %(line_items)s, %(shipping_address)s, %(billing_address)s,
        %(customer_journey)s, %(shopify_created_at)s, %(shopify_updated_at)s, %(processed_at)s, %(closed_at)s,
        %(cancelled_at)s
    )
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        customer_id = EXCLUDED.customer_id,
        total_price_amount = EXCLUDED.total_price_amount,
        total_price_currency = EXCLUDED.total_price_currency,
        subtotal_price_amount = EXCLUDED.subtotal_price_amount,
        subtotal_price_currency = EXCLUDED.subtotal_price_currency,
        total_tax_amount = EXCLUDED.total_tax_amount,
        total_tax_currency = EXCLUDED.total_tax_currency,
        total_shipping_amount = EXCLUDED.total_shipping_amount,
        total_shipping_currency = EXCLUDED.total_shipping_currency,
        financial_status = EXCLUDED.financial_status,
        fulfillment_status = EXCLUDED.fulfillment_status,
        cancelled = EXCLUDED.cancelled,
        cancel_reason = EXCLUDED.cancel_reason,
        tags = EXCLUDED.tags,
        note = EXCLUDED.note,
        line_items = EXCLUDED.line_items,
        shipping_address = EXCLUDED.shipping_address,
        billing_address = EXCLUDED.billing_address,
        customer_journey = EXCLUDED.customer_journey,
        shopify_updated_at = EXCLUDED.shopify_updated_at,
        processed_at = EXCLUDED.processed_at,
        closed_at = EXCLUDED.closed_at,
        cancelled_at = EXCLUDED.cancelled_at,
        last_sync_at = CURRENT_TIMESTAMP
    """
    
    # Process order data
    total_price = order_data.get('totalPriceSet', {}).get('shopMoney', {})
    subtotal_price = order_data.get('subtotalPriceSet', {}).get('shopMoney', {})
    total_tax = order_data.get('totalTaxSet', {}).get('shopMoney', {})
    total_shipping = order_data.get('totalShippingPriceSet', {}).get('shopMoney', {})
    
    params = {
        'id': int(order_data['id'].split('/')[-1]),
        'name': order_data.get('name'),
        'email': order_data.get('email'),
        'customer_id': int(order_data.get('customer', {}).get('id', '0').split('/')[-1]) if order_data.get('customer') else None,
        'total_price_amount': float(total_price.get('amount', 0)),
        'total_price_currency': total_price.get('currencyCode'),
        'subtotal_price_amount': float(subtotal_price.get('amount', 0)),
        'subtotal_price_currency': subtotal_price.get('currencyCode'),
        'total_tax_amount': float(total_tax.get('amount', 0)),
        'total_tax_currency': total_tax.get('currencyCode'),
        'total_shipping_amount': float(total_shipping.get('amount', 0)),
        'total_shipping_currency': total_shipping.get('currencyCode'),
        'financial_status': order_data.get('financialStatus'),
        'fulfillment_status': order_data.get('fulfillmentStatus'),
        'cancelled': order_data.get('cancelled', False),
        'cancel_reason': order_data.get('cancelReason'),
        'tags': order_data.get('tags', []),
        'note': order_data.get('note'),
        'line_items': json.dumps(order_data.get('lineItems', {})),
        'shipping_address': json.dumps(order_data.get('shippingAddress', {})),
        'billing_address': json.dumps(order_data.get('billingAddress', {})),
        'customer_journey': json.dumps(order_data.get('customerJourney', {})),
        'shopify_created_at': order_data.get('createdAt'),
        'shopify_updated_at': order_data.get('updatedAt'),
        'processed_at': order_data.get('processedAt'),
        'closed_at': order_data.get('closedAt'),
        'cancelled_at': order_data.get('cancelledAt')
    }
    
    execute_insert(query, params)


def upsert_product_variant(variant_data: Dict[str, Any]):
    """Insert or update product variant data"""
    
    query = """
    INSERT INTO product_variants (
        id, product_id, title, sku, barcode, price, compare_at_price,
        available_for_sale, inventory_quantity, weight, weight_unit,
        inventory_policy, created_at, updated_at, selected_options,
        metafields, shopify_created_at, shopify_updated_at
    ) VALUES (
        %(id)s, %(product_id)s, %(title)s, %(sku)s, %(barcode)s, %(price)s, %(compare_at_price)s,
        %(available_for_sale)s, %(inventory_quantity)s, %(weight)s, %(weight_unit)s,
        %(inventory_policy)s, %(created_at)s, %(updated_at)s, %(selected_options)s,
        %(metafields)s, %(shopify_created_at)s, %(shopify_updated_at)s
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        sku = EXCLUDED.sku,
        barcode = EXCLUDED.barcode,
        price = EXCLUDED.price,
        compare_at_price = EXCLUDED.compare_at_price,
        available_for_sale = EXCLUDED.available_for_sale,
        inventory_quantity = EXCLUDED.inventory_quantity,
        weight = EXCLUDED.weight,
        weight_unit = EXCLUDED.weight_unit,
        inventory_policy = EXCLUDED.inventory_policy,
        updated_at = EXCLUDED.updated_at,
        selected_options = EXCLUDED.selected_options,
        metafields = EXCLUDED.metafields,
        shopify_updated_at = EXCLUDED.shopify_updated_at,
        last_sync_at = CURRENT_TIMESTAMP
    """
    
    params = {
        'id': int(variant_data['id'].split('/')[-1]),
        'product_id': variant_data.get('product_id'),
        'title': variant_data.get('title'),
        'sku': variant_data.get('sku'),
        'barcode': variant_data.get('barcode'),
        'price': float(variant_data.get('price', 0)),
        'compare_at_price': float(variant_data.get('compareAtPrice', 0)) if variant_data.get('compareAtPrice') else None,
        'available_for_sale': variant_data.get('availableForSale', False),
        'inventory_quantity': variant_data.get('inventoryQuantity', 0),
        'weight': float(variant_data.get('weight', 0)) if variant_data.get('weight') else None,
        'weight_unit': variant_data.get('weightUnit'),
        'inventory_policy': variant_data.get('inventoryPolicy'),
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'selected_options': json.dumps(variant_data.get('selectedOptions', [])),
        'metafields': json.dumps(variant_data.get('metafields', {})),
        'shopify_created_at': variant_data.get('createdAt'),
        'shopify_updated_at': variant_data.get('updatedAt')
    }
    
    execute_insert(query, params)


def upsert_product_image(image_data: Dict[str, Any]):
    """Insert or update product image data"""
    
    query = """
    INSERT INTO product_images (
        id, product_id, url, alt_text, width, height, created_at, updated_at
    ) VALUES (
        %(id)s, %(product_id)s, %(url)s, %(alt_text)s, %(width)s, %(height)s, %(created_at)s, %(updated_at)s
    )
    ON CONFLICT (id) DO UPDATE SET
        url = EXCLUDED.url,
        alt_text = EXCLUDED.alt_text,
        width = EXCLUDED.width,
        height = EXCLUDED.height,
        updated_at = EXCLUDED.updated_at,
        last_sync_at = CURRENT_TIMESTAMP
    """
    
    params = {
        'id': int(image_data['id'].split('/')[-1]),
        'product_id': image_data.get('product_id'),
        'url': image_data.get('url'),
        'alt_text': image_data.get('altText'),
        'width': image_data.get('width'),
        'height': image_data.get('height'),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    execute_insert(query, params)