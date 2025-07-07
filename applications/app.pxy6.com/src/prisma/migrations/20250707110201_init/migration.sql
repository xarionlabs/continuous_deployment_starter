-- CreateTable
CREATE TABLE "Session" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "shop" TEXT NOT NULL,
    "state" TEXT NOT NULL,
    "isOnline" BOOLEAN NOT NULL DEFAULT false,
    "scope" TEXT,
    "expires" DATETIME,
    "accessToken" TEXT NOT NULL,
    "userId" BIGINT,
    "firstName" TEXT,
    "lastName" TEXT,
    "email" TEXT,
    "accountOwner" BOOLEAN NOT NULL DEFAULT false,
    "locale" TEXT,
    "collaborator" BOOLEAN DEFAULT false,
    "emailVerified" BOOLEAN DEFAULT false
);

-- CreateTable
CREATE TABLE "waiting_list" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT NOT NULL,
    "source" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "follow_up_info" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT NOT NULL,
    "role" TEXT,
    "role_other" TEXT,
    "platforms" TEXT,
    "monthly_traffic" TEXT,
    "website_name" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "loi_clicks" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "products" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "title" TEXT NOT NULL,
    "handle" TEXT NOT NULL,
    "description" TEXT,
    "descriptionHtml" TEXT,
    "productType" TEXT,
    "vendor" TEXT,
    "tags" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'ACTIVE',
    "createdAt" DATETIME NOT NULL,
    "updatedAt" DATETIME NOT NULL,
    "publishedAt" DATETIME,
    "templateSuffix" TEXT,
    "giftCardTemplateSuffix" TEXT,
    "totalInventory" INTEGER,
    "tracksQuantity" BOOLEAN NOT NULL DEFAULT false,
    "onlineStoreUrl" TEXT,
    "onlineStorePreviewUrl" TEXT,
    "requiresSellingPlan" BOOLEAN NOT NULL DEFAULT false,
    "isGiftCard" BOOLEAN NOT NULL DEFAULT false,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "product_variants" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "productId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "price" DECIMAL NOT NULL,
    "compareAtPrice" DECIMAL,
    "sku" TEXT,
    "barcode" TEXT,
    "grams" INTEGER,
    "weight" REAL,
    "weightUnit" TEXT,
    "inventoryQuantity" INTEGER,
    "inventoryManagement" TEXT,
    "inventoryPolicy" TEXT,
    "fulfillmentService" TEXT,
    "requiresShipping" BOOLEAN NOT NULL DEFAULT true,
    "taxable" BOOLEAN NOT NULL DEFAULT true,
    "taxCode" TEXT,
    "position" INTEGER,
    "option1" TEXT,
    "option2" TEXT,
    "option3" TEXT,
    "imageId" TEXT,
    "availableForSale" BOOLEAN NOT NULL DEFAULT true,
    "displayName" TEXT,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "product_variants_productId_fkey" FOREIGN KEY ("productId") REFERENCES "products" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "product_variants_imageId_fkey" FOREIGN KEY ("imageId") REFERENCES "product_images" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "product_images" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "productId" TEXT NOT NULL,
    "src" TEXT NOT NULL,
    "altText" TEXT,
    "width" INTEGER,
    "height" INTEGER,
    "position" INTEGER,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "product_images_productId_fkey" FOREIGN KEY ("productId") REFERENCES "products" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "collections" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "title" TEXT NOT NULL,
    "handle" TEXT NOT NULL,
    "description" TEXT,
    "descriptionHtml" TEXT,
    "sortOrder" TEXT,
    "templateSuffix" TEXT,
    "disjunctive" BOOLEAN NOT NULL DEFAULT false,
    "rules" TEXT,
    "ruleSet" TEXT,
    "publishedAt" DATETIME,
    "publishedScope" TEXT,
    "updatedAt" DATETIME NOT NULL,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "product_collections" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "productId" TEXT NOT NULL,
    "collectionId" TEXT NOT NULL,
    "position" INTEGER,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "product_collections_productId_fkey" FOREIGN KEY ("productId") REFERENCES "products" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "product_collections_collectionId_fkey" FOREIGN KEY ("collectionId") REFERENCES "collections" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "product_metafields" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "productId" TEXT NOT NULL,
    "namespace" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "description" TEXT,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "product_metafields_productId_fkey" FOREIGN KEY ("productId") REFERENCES "products" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "product_options" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "productId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "position" INTEGER,
    "values" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "product_options_productId_fkey" FOREIGN KEY ("productId") REFERENCES "products" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "customers" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "email" TEXT,
    "firstName" TEXT,
    "lastName" TEXT,
    "phone" TEXT,
    "acceptsMarketing" BOOLEAN NOT NULL DEFAULT false,
    "acceptsMarketingUpdatedAt" DATETIME,
    "marketingOptInLevel" TEXT,
    "ordersCount" INTEGER NOT NULL DEFAULT 0,
    "state" TEXT,
    "totalSpent" DECIMAL NOT NULL DEFAULT 0.00,
    "totalSpentCurrency" TEXT,
    "averageOrderValue" DECIMAL,
    "tags" TEXT NOT NULL,
    "note" TEXT,
    "verifiedEmail" BOOLEAN NOT NULL DEFAULT false,
    "multipassIdentifier" TEXT,
    "taxExempt" BOOLEAN NOT NULL DEFAULT false,
    "taxExemptions" TEXT NOT NULL,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "orders" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "customerId" TEXT,
    "orderNumber" INTEGER,
    "name" TEXT,
    "email" TEXT,
    "phone" TEXT,
    "financialStatus" TEXT,
    "fulfillmentStatus" TEXT,
    "currency" TEXT,
    "totalPrice" DECIMAL NOT NULL,
    "subtotalPrice" DECIMAL NOT NULL,
    "totalDiscounts" DECIMAL NOT NULL DEFAULT 0.00,
    "totalLineItemsPrice" DECIMAL NOT NULL,
    "totalTax" DECIMAL NOT NULL DEFAULT 0.00,
    "totalShippingPrice" DECIMAL NOT NULL DEFAULT 0.00,
    "totalWeight" INTEGER,
    "taxesIncluded" BOOLEAN NOT NULL DEFAULT false,
    "confirmed" BOOLEAN NOT NULL DEFAULT true,
    "cancelled" BOOLEAN NOT NULL DEFAULT false,
    "cancelledAt" DATETIME,
    "cancelReason" TEXT,
    "closedAt" DATETIME,
    "test" BOOLEAN NOT NULL DEFAULT false,
    "browserIp" TEXT,
    "landingSite" TEXT,
    "orderStatusUrl" TEXT,
    "referringSite" TEXT,
    "sourceIdentifier" TEXT,
    "sourceName" TEXT,
    "sourceUrl" TEXT,
    "tags" TEXT NOT NULL,
    "note" TEXT,
    "noteAttributes" TEXT,
    "processedAt" DATETIME,
    "legacyResourceId" TEXT,
    "shopifyCreatedAt" DATETIME NOT NULL,
    "shopifyUpdatedAt" DATETIME NOT NULL,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "orders_customerId_fkey" FOREIGN KEY ("customerId") REFERENCES "customers" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "order_line_items" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "orderId" TEXT NOT NULL,
    "productId" TEXT,
    "variantId" TEXT,
    "title" TEXT NOT NULL,
    "name" TEXT,
    "sku" TEXT,
    "vendor" TEXT,
    "quantity" INTEGER NOT NULL,
    "price" DECIMAL NOT NULL,
    "totalDiscount" DECIMAL NOT NULL DEFAULT 0.00,
    "fulfillmentStatus" TEXT,
    "fulfillmentService" TEXT,
    "giftCard" BOOLEAN NOT NULL DEFAULT false,
    "grams" INTEGER,
    "properties" TEXT,
    "taxable" BOOLEAN NOT NULL DEFAULT true,
    "taxLines" TEXT,
    "tipPaymentGateway" TEXT,
    "tipPaymentMethod" TEXT,
    "totalDiscountSet" TEXT,
    "variantInventoryManagement" TEXT,
    "variantTitle" TEXT,
    "requiresShipping" BOOLEAN NOT NULL DEFAULT true,
    "legacyResourceId" TEXT,
    "syncedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "order_line_items_orderId_fkey" FOREIGN KEY ("orderId") REFERENCES "orders" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "order_line_items_productId_fkey" FOREIGN KEY ("productId") REFERENCES "products" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "order_line_items_variantId_fkey" FOREIGN KEY ("variantId") REFERENCES "product_variants" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "sync_logs" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "entityType" TEXT NOT NULL,
    "operation" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "startedAt" DATETIME NOT NULL,
    "completedAt" DATETIME,
    "errorMessage" TEXT,
    "recordsProcessed" INTEGER,
    "recordsCreated" INTEGER,
    "recordsUpdated" INTEGER,
    "recordsSkipped" INTEGER,
    "lastCursor" TEXT,
    "metadata" TEXT
);

-- CreateTable
CREATE TABLE "sync_states" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "entityType" TEXT NOT NULL,
    "lastSyncAt" DATETIME NOT NULL,
    "lastCursor" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT false,
    "syncVersion" TEXT,
    "metadata" TEXT,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "webhook_events" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "shopifyId" TEXT,
    "topic" TEXT NOT NULL,
    "shop" TEXT NOT NULL,
    "payload" TEXT NOT NULL,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "processedAt" DATETIME,
    "errorMessage" TEXT,
    "attempts" INTEGER NOT NULL DEFAULT 0,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateIndex
CREATE UNIQUE INDEX "waiting_list_email_key" ON "waiting_list"("email");

-- CreateIndex
CREATE UNIQUE INDEX "products_handle_key" ON "products"("handle");

-- CreateIndex
CREATE UNIQUE INDEX "collections_handle_key" ON "collections"("handle");

-- CreateIndex
CREATE UNIQUE INDEX "product_collections_productId_collectionId_key" ON "product_collections"("productId", "collectionId");

-- CreateIndex
CREATE UNIQUE INDEX "product_metafields_productId_namespace_key_key" ON "product_metafields"("productId", "namespace", "key");

-- CreateIndex
CREATE UNIQUE INDEX "sync_states_entityType_key" ON "sync_states"("entityType");
