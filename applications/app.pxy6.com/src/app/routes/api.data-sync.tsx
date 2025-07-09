import { json } from "@remix-run/node";
import type { ActionFunctionArgs } from "@remix-run/node";
import { withCors } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";
import prisma from "../db.server";

/**
 * API Routes for Shopify Data Sync
 * 
 * Endpoints:
 * - POST /api/data-sync - Trigger Shopify data sync DAGs
 * - GET /api/data-sync/status/{runId} - Check DAG run status
 */

// Inline Airflow client functions to avoid import issues
let jwtToken: string | null = null;

const getJwtToken = async (): Promise<string> => {
  if (jwtToken) return jwtToken;
  
  const baseUrl = process.env.AIRFLOW_API_URL || 'http://localhost:8080/api/v2';
  const username = process.env.AIRFLOW_USERNAME || 'admin';
  const password = process.env.AIRFLOW_PASSWORD || 'admin';
  const nodeEnv = process.env.NODE_ENV || 'development';
  
  // For local development with standalone Airflow, get JWT token
  if (nodeEnv === 'development' || baseUrl.includes('localhost')) {
    const authUrl = `${baseUrl.replace('/api/v2', '')}/auth/token`;
    
    const response = await fetch(authUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        password,
      }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Airflow token request failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const tokenData = await response.json();
    jwtToken = `Bearer ${tokenData.access_token}`;
    return jwtToken;
  }
  
  // For staging/live with Google OAuth, we'll need to implement OAuth flow
  // For now, throw an error to indicate this needs to be implemented
  throw new Error('Google OAuth authentication for staging/live environments not yet implemented');
};

const createAirflowRequest = async (endpoint: string, options: RequestInit = {}) => {
  const baseUrl = process.env.AIRFLOW_API_URL || 'http://localhost:8080/api/v2';
  
  // Get authentication token/cookie
  const authToken = await getJwtToken();
  
  const url = `${baseUrl}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': authToken, // Use Basic auth for local, will be different for OAuth
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      ...options.headers,
    },
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const errorText = await response.text();
    // If we get 401, try to refresh the auth
    if (response.status === 401) {
      jwtToken = null;
      const newToken = await getJwtToken();
      const retryResponse = await fetch(url, {
        ...options,
        headers: {
          'Authorization': newToken,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          ...options.headers,
        },
        signal: AbortSignal.timeout(30000),
      });
      
      if (!retryResponse.ok) {
        const retryErrorText = await retryResponse.text();
        throw new Error(`Airflow API error: ${retryResponse.status} ${retryResponse.statusText} - ${retryErrorText}`);
      }
      
      return retryResponse.json();
    }
    
    throw new Error(`Airflow API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.json();
};

const testAirflowConnection = async (): Promise<boolean> => {
  try {
    await createAirflowRequest('/monitor/health');
    return true;
  } catch (error) {
    console.error('Airflow connection test failed:', error);
    return false;
  }
};

const triggerDataSync = async (config: {
  syncMode?: 'full' | 'incremental';
  enableProducts?: boolean;
  enableCustomers?: boolean;
  enableOrders?: boolean;
  note?: string;
  shopDomain?: string;
  accessToken?: string;
  shopId?: string;
}) => {
  const dagId = 'shopify_sync';
  
  const requestBody = {
    // Let Airflow generate the dag_run_id automatically
    logical_date: new Date().toISOString(),
    conf: {
      sync_mode: config.syncMode || 'incremental',
      enable_products_sync: config.enableProducts !== false,
      enable_customers_sync: config.enableCustomers !== false,
      enable_orders_sync: config.enableOrders !== false,
      // Shop-specific data for multi-tenant support
      shop_domain: config.shopDomain,
      access_token: config.accessToken,
      shop_id: config.shopId,
      triggered_by: 'app_pxy6_com',
      trigger_time: new Date().toISOString(),
    },
    note: config.note || 'Triggered from app.pxy6.com data dashboard',
  };

  return createAirflowRequest(`/dags/${dagId}/dagRuns`, {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });
};

// getDagRunStatus and getTaskInstances moved to api.data-sync.status.$runId.tsx

// This file only handles POST /api/data-sync (triggering sync)
// Status checking is handled by api.data-sync.status.$runId.tsx

// Helper function to create sync log entry
const createSyncLogEntry = async (entityType: string, operation: string, status: string, runId?: string, errorMessage?: string) => {
  try {
    const now = new Date();
    const logId = `sync_log_${entityType}_${operation}_${runId || Date.now()}`;
    
    await (prisma as any).syncLog?.create({
      data: {
        id: logId,
        entityType,
        operation,
        status,
        startedAt: now,
        completedAt: status === 'completed' || status === 'failed' ? now : null,
        errorMessage,
        recordsProcessed: 0,
        recordsCreated: 0,
        recordsUpdated: 0,
      },
    });
  } catch (error) {
    console.error('Failed to create sync log entry:', error);
    // Don't throw - this is just logging
  }
};

// POST /api/data-sync - Trigger data sync
export const action = withCors(async ({ request }: ActionFunctionArgs) => {
  if (request.method !== 'POST') {
    return json({
      success: false,
      error: 'Method not allowed',
    }, { status: 405 });
  }

  try {
    // Get Shopify session for shop-specific data
    const { session } = await authenticate.admin(request);
    const { shop, accessToken } = session;
    
    // Extract shop domain (remove .myshopify.com suffix if present)
    const shopDomain = shop.replace('.myshopify.com', '');

    const body = await request.json();
    const {
      syncMode = 'incremental',
      enableProducts = true,
      enableCustomers = true,
      enableOrders = true,
      note,
    } = body;

    // Validate sync mode
    if (!['full', 'incremental'].includes(syncMode)) {
      return json({
        success: false,
        error: 'Invalid sync mode. Must be "full" or "incremental"',
      }, { status: 400 });
    }

    // Test connection before triggering
    const isConnected = await testAirflowConnection();
    if (!isConnected) {
      return json({
        success: false,
        error: 'Unable to connect to Airflow service',
      }, { status: 503 });
    }

    // Trigger the DAG with shop-specific data (let Airflow generate the runId)
    const dagRun = await triggerDataSync({
      syncMode,
      enableProducts,
      enableCustomers,
      enableOrders,
      note,
      shopDomain,
      accessToken,
      shopId: shop, // Use full shop domain as shop ID
    });

    // Log sync request with the actual runId from Airflow
    await createSyncLogEntry('all', 'sync_request', 'requested', dagRun.dag_run_id);

    return json({
      success: true,
      data: {
        runId: dagRun.dag_run_id, // Use dag_run_id as the runId for polling
        dagRunId: dagRun.dag_run_id,
        state: dagRun.state,
        executionDate: dagRun.execution_date,
        configuration: dagRun.conf,
      },
      message: 'Data sync triggered successfully',
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Failed to trigger data sync:', error);
    
    return json({
      success: false,
      error: error instanceof Error ? error.message : 'Failed to trigger data sync',
    }, { status: 500 });
  }
});