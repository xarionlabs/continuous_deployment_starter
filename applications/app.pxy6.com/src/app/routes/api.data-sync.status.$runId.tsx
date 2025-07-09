import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { withCorsLoader } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";

/**
 * API Route for Checking DAG Run Status
 * 
 * Endpoint:
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

const getDagRunStatus = async (runId: string) => {
  const dagId = 'shopify_sync';
  return createAirflowRequest(`/dags/${dagId}/dagRuns/${runId}`);
};

const getTaskInstances = async (runId: string) => {
  const dagId = 'shopify_sync';
  return createAirflowRequest(`/dags/${dagId}/dagRuns/${runId}/taskInstances`);
};

// GET /api/data-sync/status/{runId}
export const loader = withCorsLoader(async ({ request, params }: LoaderFunctionArgs) => {
  const { runId } = params;
  
  try {
    // Authenticate with Shopify to ensure only valid app users can check status
    await authenticate.admin(request);
    
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

  } catch (error) {
    console.error('Data sync status API error:', error);
    
    return json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    }, { status: 500 });
  }
});