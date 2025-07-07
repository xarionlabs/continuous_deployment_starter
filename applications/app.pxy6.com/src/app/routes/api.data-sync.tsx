import { json } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { withCors, withCorsLoader } from "../utils/cors.injector";

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
  
  const response = await fetch(`${baseUrl.replace('/api/v2', '')}/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: username,
      password: password,
    }),
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`JWT token request failed: ${response.status} ${response.statusText} - ${errorText}`);
  }

  const tokenData = await response.json();
  jwtToken = tokenData.access_token;
  return jwtToken as string;
};

const createAirflowRequest = async (endpoint: string, options: RequestInit = {}) => {
  const baseUrl = process.env.AIRFLOW_API_URL || 'http://localhost:8080/api/v2';
  const token = await getJwtToken();
  const url = `${baseUrl}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    },
    signal: AbortSignal.timeout(30000),
  });

  if (!response.ok) {
    const errorText = await response.text();
    // If we get 401, try to refresh the token
    if (response.status === 401) {
      jwtToken = null;
      const newToken = await getJwtToken();
      const retryResponse = await fetch(url, {
        ...options,
        headers: {
          'Authorization': `Bearer ${newToken}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
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
}) => {
  const dagId = 'shopify_data_pipeline';
  const runId = `manual_${Date.now()}`;
  
  const requestBody = {
    dag_run_id: runId,
    logical_date: new Date().toISOString(),
    conf: {
      sync_mode: config.syncMode || 'incremental',
      enable_products_sync: config.enableProducts !== false,
      enable_customers_sync: config.enableCustomers !== false,
      enable_orders_sync: config.enableOrders !== false,
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
  const dagId = 'shopify_data_pipeline';
  return createAirflowRequest(`/dags/${dagId}/dagRuns/${runId}`);
};

const getTaskInstances = async (runId: string) => {
  const dagId = 'shopify_data_pipeline';
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

    // Trigger the DAG
    const dagRun = await triggerDataSync({
      syncMode,
      enableProducts,
      enableCustomers,
      enableOrders,
      note,
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