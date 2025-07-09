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

# Reduce PostgresHook logging verbosity
postgres_logger = logging.getLogger("airflow.providers.postgres.hooks.postgres")
postgres_logger.setLevel(logging.WARNING)


# Database connection utilities
def get_postgres_hook() -> PostgresHook:
    """Get a PostgresHook instance for pxy6 database"""
    return PostgresHook(postgres_conn_id="pxy6_postgres")


def execute_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a query using Airflow PostgresHook"""
    try:
        hook = get_postgres_hook()
        return hook.get_records(query, parameters)
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        raise


def execute_insert(query: str, parameters: Optional[List[Any]] = None) -> None:
    """Execute an insert/update query using Airflow PostgresHook"""
    try:
        hook = get_postgres_hook()
        hook.run(query, parameters=parameters)
    except Exception as e:
        logger.error(f"Database insert failed: {str(e)}")
        raise


# Shopify data upsert functions
def upsert_customer(customer_data: Dict[str, Any], shop: str):
    """Insert or update customer data"""
    if not customer_data or not customer_data.get("id"):
        raise ValueError("Customer data must contain valid 'id' field")
    if not shop:
        raise ValueError("Shop parameter is required")

    query = """
    INSERT INTO customers (
        id, shop, email, "firstName", "lastName", phone, "acceptsMarketing", 
        "acceptsMarketingUpdatedAt", "marketingOptInLevel", "ordersCount", state,
        "totalSpent", "totalSpentCurrency", "averageOrderValue", tags, note,
        "verifiedEmail", "multipassIdentifier", "taxExempt", "taxExemptions",
        "legacyResourceId", "shopifyCreatedAt", "shopifyUpdatedAt", "syncedAt"
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        "firstName" = EXCLUDED."firstName",
        "lastName" = EXCLUDED."lastName",
        phone = EXCLUDED.phone,
        "acceptsMarketing" = EXCLUDED."acceptsMarketing",
        "acceptsMarketingUpdatedAt" = EXCLUDED."acceptsMarketingUpdatedAt",
        "marketingOptInLevel" = EXCLUDED."marketingOptInLevel",
        "ordersCount" = EXCLUDED."ordersCount",
        state = EXCLUDED.state,
        "totalSpent" = EXCLUDED."totalSpent",
        "totalSpentCurrency" = EXCLUDED."totalSpentCurrency",
        "averageOrderValue" = EXCLUDED."averageOrderValue",
        tags = EXCLUDED.tags,
        note = EXCLUDED.note,
        "verifiedEmail" = EXCLUDED."verifiedEmail",
        "multipassIdentifier" = EXCLUDED."multipassIdentifier",
        "taxExempt" = EXCLUDED."taxExempt",
        "taxExemptions" = EXCLUDED."taxExemptions",
        "legacyResourceId" = EXCLUDED."legacyResourceId",
        "shopifyUpdatedAt" = EXCLUDED."shopifyUpdatedAt",
        "syncedAt" = CURRENT_TIMESTAMP
    """

    # Process customer data to extract fields
    total_spent = customer_data.get("totalSpentV2", {})

    # Handle required NOT NULL fields with defaults
    created_at = customer_data.get("createdAt")
    updated_at = customer_data.get("updatedAt")

    # If updatedAt is null/missing, use createdAt as fallback, or current time as last resort
    if not updated_at:
        updated_at = created_at if created_at else datetime.now().isoformat()

    # If createdAt is null/missing, use current time
    if not created_at:
        created_at = datetime.now().isoformat()

    params = [
        customer_data["id"],  # Use full Shopify GID
        shop,  # Shop domain
        customer_data.get("email"),
        customer_data.get("firstName"),
        customer_data.get("lastName"),
        customer_data.get("phone"),
        customer_data.get("acceptsMarketing", False),
        customer_data.get("acceptsMarketingUpdatedAt"),
        customer_data.get("marketingOptInLevel"),
        customer_data.get("numberOfOrders", 0),
        customer_data.get("state"),
        float(total_spent.get("amount", 0)) if total_spent.get("amount") else 0,
        total_spent.get("currencyCode"),
        customer_data.get("averageOrderValue"),
        json.dumps(customer_data.get("tags", [])),
        customer_data.get("note"),
        customer_data.get("verifiedEmail", False),
        customer_data.get("multipassIdentifier"),
        customer_data.get("taxExempt", False),
        json.dumps(customer_data.get("taxExemptions", [])),
        customer_data.get("legacyResourceId"),
        created_at,
        updated_at,
        datetime.now(),
    ]

    execute_insert(query, params)


def upsert_product(product_data: Dict[str, Any], shop: str):
    """Insert or update product data"""
    if not product_data or not product_data.get("id"):
        raise ValueError("Product data must contain valid 'id' field")
    if not shop:
        raise ValueError("Shop parameter is required")

    query = """
    INSERT INTO products (
        id, shop, title, handle, description, "descriptionHtml", "productType", vendor,
        tags, status, "totalInventory", "onlineStoreUrl", "templateSuffix",
        "giftCardTemplateSuffix", "tracksQuantity", "onlineStorePreviewUrl", 
        "requiresSellingPlan", "isGiftCard", "legacyResourceId", "shopifyCreatedAt",
        "shopifyUpdatedAt", "publishedAt", "createdAt", "updatedAt", "syncedAt"
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        handle = EXCLUDED.handle,
        description = EXCLUDED.description,
        "descriptionHtml" = EXCLUDED."descriptionHtml",
        "productType" = EXCLUDED."productType",
        vendor = EXCLUDED.vendor,
        tags = EXCLUDED.tags,
        status = EXCLUDED.status,
        "totalInventory" = EXCLUDED."totalInventory",
        "onlineStoreUrl" = EXCLUDED."onlineStoreUrl",
        "templateSuffix" = EXCLUDED."templateSuffix",
        "giftCardTemplateSuffix" = EXCLUDED."giftCardTemplateSuffix",
        "tracksQuantity" = EXCLUDED."tracksQuantity",
        "onlineStorePreviewUrl" = EXCLUDED."onlineStorePreviewUrl",
        "requiresSellingPlan" = EXCLUDED."requiresSellingPlan",
        "isGiftCard" = EXCLUDED."isGiftCard",
        "legacyResourceId" = EXCLUDED."legacyResourceId",
        "shopifyUpdatedAt" = EXCLUDED."shopifyUpdatedAt",
        "publishedAt" = EXCLUDED."publishedAt",
        "updatedAt" = EXCLUDED."updatedAt",
        "syncedAt" = CURRENT_TIMESTAMP
    """

    # Handle required NOT NULL fields with defaults
    title = product_data.get("title") or "Untitled Product"
    handle = product_data.get("handle") or f"product-{product_data['id']}"
    created_at = product_data.get("createdAt")
    updated_at = product_data.get("updatedAt")

    # If updatedAt is null/missing, use createdAt as fallback, or current time as last resort
    if not updated_at:
        updated_at = created_at if created_at else datetime.now().isoformat()

    # If createdAt is null/missing, use current time
    if not created_at:
        created_at = datetime.now().isoformat()

    params = [
        product_data["id"],  # Use full Shopify GID
        shop,  # Shop domain
        title,
        handle,
        product_data.get("description"),
        product_data.get("descriptionHtml"),
        product_data.get("productType"),
        product_data.get("vendor"),
        json.dumps(product_data.get("tags", [])),
        product_data.get("status", "ACTIVE"),
        product_data.get("totalInventory"),
        product_data.get("onlineStoreUrl"),
        product_data.get("templateSuffix"),
        product_data.get("giftCardTemplateSuffix"),
        product_data.get("tracksQuantity", False),
        product_data.get("onlineStorePreviewUrl"),
        product_data.get("requiresSellingPlan", False),
        product_data.get("isGiftCard", False),
        product_data.get("legacyResourceId"),
        created_at,
        updated_at,
        product_data.get("publishedAt"),
        datetime.now(),
        datetime.now(),
        datetime.now(),
    ]

    execute_insert(query, params)


def upsert_order(order_data: Dict[str, Any], shop: str):
    """Insert or update order data"""
    if not order_data or not order_data.get("id"):
        raise ValueError("Order data must contain valid 'id' field")
    if not shop:
        raise ValueError("Shop parameter is required")

    query = """
    INSERT INTO orders (
        id, shop, "customerId", "orderNumber", name, email, phone, "financialStatus", 
        "fulfillmentStatus", currency, "totalPrice", "subtotalPrice", "totalDiscounts",
        "totalLineItemsPrice", "totalTax", "totalShippingPrice", "totalWeight",
        "taxesIncluded", confirmed, cancelled, "cancelledAt", "cancelReason",
        "closedAt", test, "browserIp", "landingSite", "orderStatusUrl",
        "referringSite", "sourceIdentifier", "sourceName", "sourceUrl", tags,
        note, "noteAttributes", "processedAt", "legacyResourceId", 
        "shopifyCreatedAt", "shopifyUpdatedAt", "syncedAt"
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s
    )
    ON CONFLICT (id) DO UPDATE SET
        "customerId" = EXCLUDED."customerId",
        "orderNumber" = EXCLUDED."orderNumber",
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        phone = EXCLUDED.phone,
        "financialStatus" = EXCLUDED."financialStatus",
        "fulfillmentStatus" = EXCLUDED."fulfillmentStatus",
        currency = EXCLUDED.currency,
        "totalPrice" = EXCLUDED."totalPrice",
        "subtotalPrice" = EXCLUDED."subtotalPrice",
        "totalDiscounts" = EXCLUDED."totalDiscounts",
        "totalLineItemsPrice" = EXCLUDED."totalLineItemsPrice",
        "totalTax" = EXCLUDED."totalTax",
        "totalShippingPrice" = EXCLUDED."totalShippingPrice",
        "totalWeight" = EXCLUDED."totalWeight",
        "taxesIncluded" = EXCLUDED."taxesIncluded",
        confirmed = EXCLUDED.confirmed,
        cancelled = EXCLUDED.cancelled,
        "cancelledAt" = EXCLUDED."cancelledAt",
        "cancelReason" = EXCLUDED."cancelReason",
        "closedAt" = EXCLUDED."closedAt",
        test = EXCLUDED.test,
        "browserIp" = EXCLUDED."browserIp",
        "landingSite" = EXCLUDED."landingSite",
        "orderStatusUrl" = EXCLUDED."orderStatusUrl",
        "referringSite" = EXCLUDED."referringSite",
        "sourceIdentifier" = EXCLUDED."sourceIdentifier",
        "sourceName" = EXCLUDED."sourceName",
        "sourceUrl" = EXCLUDED."sourceUrl",
        tags = EXCLUDED.tags,
        note = EXCLUDED.note,
        "noteAttributes" = EXCLUDED."noteAttributes",
        "processedAt" = EXCLUDED."processedAt",
        "legacyResourceId" = EXCLUDED."legacyResourceId",
        "shopifyUpdatedAt" = EXCLUDED."shopifyUpdatedAt",
        "syncedAt" = CURRENT_TIMESTAMP
    """

    # Process order data
    total_price = order_data.get("totalPriceSet", {}).get("shopMoney", {})
    subtotal_price = order_data.get("subtotalPriceSet", {}).get("shopMoney", {})
    total_tax = order_data.get("totalTaxSet", {}).get("shopMoney", {})
    total_shipping = order_data.get("totalShippingPriceSet", {}).get("shopMoney", {})
    total_discounts = order_data.get("totalDiscountsSet", {}).get("shopMoney", {})
    total_line_items = order_data.get("totalLineItemsPriceSet", {}).get("shopMoney", {})

    # Handle required NOT NULL fields with defaults
    created_at = order_data.get("createdAt")
    updated_at = order_data.get("updatedAt")

    # If updatedAt is null/missing, use createdAt as fallback, or current time as last resort
    if not updated_at:
        updated_at = created_at if created_at else datetime.now().isoformat()

    # If createdAt is null/missing, use current time
    if not created_at:
        created_at = datetime.now().isoformat()

    params = [
        order_data["id"],  # Use full Shopify GID
        shop,  # Shop domain
        order_data.get("customer", {}).get("id") if order_data.get("customer") else None,
        order_data.get("orderNumber"),
        order_data.get("name"),
        order_data.get("email"),
        order_data.get("phone"),
        order_data.get("financialStatus"),
        order_data.get("fulfillmentStatus"),
        order_data.get("currencyCode"),
        float(total_price.get("amount", 0)),
        float(subtotal_price.get("amount", 0)),
        float(total_discounts.get("amount", 0)),
        float(total_line_items.get("amount", 0)),
        float(total_tax.get("amount", 0)),
        float(total_shipping.get("amount", 0)),
        order_data.get("totalWeight"),
        order_data.get("taxesIncluded", False),
        order_data.get("confirmed", True),
        order_data.get("cancelled", False),
        order_data.get("cancelledAt"),
        order_data.get("cancelReason"),
        order_data.get("closedAt"),
        order_data.get("test", False),
        order_data.get("browserIp"),
        order_data.get("landingSite"),
        order_data.get("orderStatusUrl"),
        order_data.get("referringSite"),
        order_data.get("sourceIdentifier"),
        order_data.get("sourceName"),
        order_data.get("sourceUrl"),
        json.dumps(order_data.get("tags", [])),
        order_data.get("note"),
        json.dumps(order_data.get("noteAttributes", [])),
        order_data.get("processedAt"),
        order_data.get("legacyResourceId"),
        created_at,
        updated_at,
        datetime.now(),
    ]

    execute_insert(query, params)


def upsert_product_variant(variant_data: Dict[str, Any], shop: str):
    """Insert or update product variant data"""
    if not variant_data or not variant_data.get("id"):
        raise ValueError("Variant data must contain valid 'id' field")
    if not shop:
        raise ValueError("Shop parameter is required")

    query = """
    INSERT INTO product_variants (
        id, shop, "productId", title, price, "compareAtPrice", sku, barcode, grams,
        weight, "weightUnit", "inventoryQuantity", "inventoryManagement", 
        "inventoryPolicy", "fulfillmentService", "requiresShipping", taxable,
        "taxCode", position, option1, option2, option3, "imageId",
        "availableForSale", "displayName", "legacyResourceId", 
        "shopifyCreatedAt", "shopifyUpdatedAt", "syncedAt"
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s
    )
    ON CONFLICT (id) DO UPDATE SET
        "productId" = EXCLUDED."productId",
        title = EXCLUDED.title,
        price = EXCLUDED.price,
        "compareAtPrice" = EXCLUDED."compareAtPrice",
        sku = EXCLUDED.sku,
        barcode = EXCLUDED.barcode,
        grams = EXCLUDED.grams,
        weight = EXCLUDED.weight,
        "weightUnit" = EXCLUDED."weightUnit",
        "inventoryQuantity" = EXCLUDED."inventoryQuantity",
        "inventoryManagement" = EXCLUDED."inventoryManagement",
        "inventoryPolicy" = EXCLUDED."inventoryPolicy",
        "fulfillmentService" = EXCLUDED."fulfillmentService",
        "requiresShipping" = EXCLUDED."requiresShipping",
        taxable = EXCLUDED.taxable,
        "taxCode" = EXCLUDED."taxCode",
        position = EXCLUDED.position,
        option1 = EXCLUDED.option1,
        option2 = EXCLUDED.option2,
        option3 = EXCLUDED.option3,
        "imageId" = EXCLUDED."imageId",
        "availableForSale" = EXCLUDED."availableForSale",
        "displayName" = EXCLUDED."displayName",
        "legacyResourceId" = EXCLUDED."legacyResourceId",
        "shopifyUpdatedAt" = EXCLUDED."shopifyUpdatedAt",
        "syncedAt" = CURRENT_TIMESTAMP
    """

    # Process variant data safely
    def safe_get_amount(data, default=0):
        """Safely extract amount from price data"""
        if isinstance(data, dict):
            amount = data.get("amount")
            if amount is not None:
                try:
                    return float(amount)
                except (ValueError, TypeError):
                    return default
        elif isinstance(data, (int, float, str)):
            try:
                return float(data)
            except (ValueError, TypeError):
                return default
        return default

    def safe_get_weight_value(weight_data):
        """Safely extract weight value"""
        if isinstance(weight_data, dict):
            return weight_data.get("value")
        return weight_data

    def safe_get_weight_unit(weight_data):
        """Safely extract weight unit"""
        if isinstance(weight_data, dict):
            return weight_data.get("unit")
        return None

    def safe_get_option_value(options, index):
        """Safely extract option value at index"""
        if isinstance(options, list) and len(options) > index:
            option = options[index]
            if isinstance(option, dict):
                return option.get("value")
            return option
        return None

    price_data = variant_data.get("price", {})
    compare_at_price_data = variant_data.get("compareAtPrice", {})
    weight_data = variant_data.get("weight", {})
    selected_options = variant_data.get("selectedOptions", [])
    image_data = variant_data.get("image", {})

    params = [
        variant_data["id"],  # Use full Shopify GID
        shop,  # Shop domain
        variant_data.get("product_id")
        or (variant_data.get("product", {}).get("id") if isinstance(variant_data.get("product"), dict) else None),
        variant_data.get("title"),
        safe_get_amount(price_data),
        safe_get_amount(compare_at_price_data, None),
        variant_data.get("sku"),
        variant_data.get("barcode"),
        safe_get_weight_value(weight_data),
        safe_get_weight_value(weight_data),  # grams field maps to same weight value
        safe_get_weight_unit(weight_data),
        variant_data.get("inventoryQuantity"),
        variant_data.get("inventoryManagement"),
        variant_data.get("inventoryPolicy"),
        variant_data.get("fulfillmentService"),
        variant_data.get("requiresShipping", True),
        variant_data.get("taxable", True),
        variant_data.get("taxCode"),
        variant_data.get("position"),
        safe_get_option_value(selected_options, 0),
        safe_get_option_value(selected_options, 1),
        safe_get_option_value(selected_options, 2),
        image_data.get("id") if isinstance(image_data, dict) else None,
        variant_data.get("availableForSale", True),
        variant_data.get("displayName"),
        variant_data.get("legacyResourceId"),
        variant_data.get("createdAt"),
        variant_data.get("updatedAt"),
        datetime.now(),
    ]

    execute_insert(query, params)


def upsert_product_image(image_data: Dict[str, Any], shop: str):
    """Insert or update product image data"""
    if not image_data or not image_data.get("id"):
        raise ValueError("Image data must contain valid 'id' field")
    if not shop:
        raise ValueError("Shop parameter is required")

    query = """
    INSERT INTO product_images (
        id, shop, "productId", src, "altText", width, height, position,
        "legacyResourceId", "shopifyCreatedAt", "shopifyUpdatedAt", "syncedAt"
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s
    )
    ON CONFLICT (id) DO UPDATE SET
        "productId" = EXCLUDED."productId",
        src = EXCLUDED.src,
        "altText" = EXCLUDED."altText",
        width = EXCLUDED.width,
        height = EXCLUDED.height,
        position = EXCLUDED.position,
        "legacyResourceId" = EXCLUDED."legacyResourceId",
        "shopifyUpdatedAt" = EXCLUDED."shopifyUpdatedAt",
        "syncedAt" = CURRENT_TIMESTAMP
    """

    # Handle required NOT NULL fields with defaults
    created_at = image_data.get("createdAt")
    updated_at = image_data.get("updatedAt")

    # If updatedAt is null/missing, use createdAt as fallback, or current time as last resort
    if not updated_at:
        updated_at = created_at if created_at else datetime.now().isoformat()

    # If createdAt is null/missing, use current time
    if not created_at:
        created_at = datetime.now().isoformat()

    params = [
        image_data["id"],  # Use full Shopify GID
        shop,  # Shop domain
        image_data.get("product_id")
        or (image_data.get("product", {}).get("id") if isinstance(image_data.get("product"), dict) else None),
        image_data.get("src") or image_data.get("url"),
        image_data.get("altText"),
        image_data.get("width"),
        image_data.get("height"),
        image_data.get("position"),
        image_data.get("legacyResourceId"),
        created_at,
        updated_at,
        datetime.now(),
    ]

    execute_insert(query, params)


def upsert_sync_log(
    entity_type: str,
    operation: str,
    status: str,
    shop: str,
    records_processed: int = 0,
    records_created: int = 0,
    records_updated: int = 0,
    error_message: str = None,
):
    """Insert a sync log entry"""
    query = """
    INSERT INTO sync_logs (
        id, shop, "entityType", operation, status, "startedAt", "completedAt", 
        "recordsProcessed", "recordsCreated", "recordsUpdated", "errorMessage"
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    now = datetime.now()
    completed_at = now if status in ["completed", "failed"] else None

    # Generate a unique ID based on entity type, operation, and timestamp
    log_id = f"sync_log_{entity_type}_{operation}_{int(now.timestamp())}"

    params = [
        log_id,
        shop,
        entity_type,
        operation,
        status,
        now,
        completed_at,
        records_processed,
        records_created,
        records_updated,
        error_message,
    ]

    execute_insert(query, params)


def upsert_sync_state(entity_type: str, shop: str, last_sync_at: datetime = None):
    """Insert or update sync state for an entity type"""
    query = """
    INSERT INTO sync_states (
        id, shop, "entityType", "lastSyncAt", "isActive", "updatedAt"
    ) VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (shop, "entityType") DO UPDATE SET
        "lastSyncAt" = EXCLUDED."lastSyncAt",
        "isActive" = EXCLUDED."isActive",
        "updatedAt" = EXCLUDED."updatedAt"
    """

    sync_time = last_sync_at or datetime.now()

    # Generate a unique ID based on entity type and timestamp
    sync_id = f"sync_state_{entity_type}_{int(sync_time.timestamp())}"

    params = [sync_id, shop, entity_type, sync_time, True, datetime.now()]

    execute_insert(query, params)
