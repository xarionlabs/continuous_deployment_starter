import { json } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { withCors, withCorsLoader } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";

/**
 * API Routes for Shopify Data Sync
 * 
 * Endpoints:
 * - POST /api/data-sync - Trigger Shopify data sync DAGs
 * - GET /api/data-sync/status/{runId} - Check DAG run status
 */

// Inline Airflow client functions to avoid import issues
const createAirflowRequest = async (endpoint: string, options: RequestInit = {}) => {
  const baseUrl = process.env.AIRFLOW_API_URL || 'http://localhost:8080/api/v2';
  const username = process.env.AIRFLOW_USERNAME || 'admin';
  const password = process.env.AIRFLOW_PASSWORD || 'admin';
  
  // Create basic auth header
  const credentials = btoa(`${username}:${password}`);
  const url = `${baseUrl}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    },
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const errorText = await response.text();
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
  const runId = `manual_${Date.now()}`;
  
  const requestBody = {
    dag_run_id: runId,
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

const getDagRunStatus = async (runId: string) => {
  const dagId = 'shopify_sync';
  return createAirflowRequest(`/dags/${dagId}/dagRuns/${runId}`);
};

const getTaskInstances = async (runId: string) => {
  const dagId = 'shopify_sync';
  return createAirflowRequest(`/dags/${dagId}/dagRuns/${runId}/taskInstances`);
};

// GET /api/data-sync/status/{runId}
export const loader = withCorsLoader(async ({ request }: LoaderFunctionArgs) => {
  const url = new URL(request.url);
  const pathname = url.pathname;

  try {
    // GET /api/data-sync/status/{runId}
    if (pathname.startsWith('/api/data-sync/status/')) {
      const runId = pathname.split('/').pop();
      
      if (!runId) {
        return json({
          success: false,
          error: 'Run ID is required',
        }, { status: 400 });
      }

      const dagRun = await getDagRunStatus(runId);
      const taskInstances = await getTaskInstances(runId);
      
      return json({
        success: true,
        data: {
          dagRun,
          taskInstances: taskInstances.task_instances,
          totalTasks: taskInstances.total_entries,
        },
        timestamp: new Date().toISOString(),
      });
    }

    return json({
      success: false,
      error: 'Endpoint not found',
    }, { status: 404 });

  } catch (error) {
    console.error('Data sync API error:', error);
    
    return json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    }, { status: 500 });
  }
});

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

    // Trigger the DAG with shop-specific data
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

    return json({
      success: true,
      data: {
        runId: dagRun.run_id,
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