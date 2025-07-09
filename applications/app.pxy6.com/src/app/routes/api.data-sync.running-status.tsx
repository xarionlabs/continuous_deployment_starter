import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { withCorsLoader } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";
import prisma from "../db.server";

/**
 * API Route for Checking Running Sync Status
 * 
 * Endpoint:
 * - GET /api/data-sync/running-status - Check if there are any running/queued DAG runs
 */

// Inline Airflow client functions for status checking only
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
      'Authorization': authToken,
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

const checkDagRunStatus = async (runId: string) => {
  const dagId = 'shopify_sync';
  return createAirflowRequest(`/dags/${dagId}/dagRuns/${runId}`);
};

const getRecentSyncRequest = async () => {
  try {
    // Get the most recent sync request from our sync log table
    const recentSyncLog = await (prisma as any).syncLog?.findFirst({
      where: {
        entityType: 'all',
        operation: 'sync_request',
        status: 'requested',
      },
      orderBy: {
        startedAt: 'desc',
      },
      select: {
        id: true,
        startedAt: true,
      },
    });

    if (!recentSyncLog) {
      return null;
    }

    // Extract runId from the log ID (format: sync_log_all_sync_request_{runId})
    const runId = recentSyncLog.id.replace('sync_log_all_sync_request_', '');
    
    // Check if this sync was started recently (within last 30 minutes)
    const thirtyMinutesAgo = new Date(Date.now() - 30 * 60 * 1000);
    if (new Date(recentSyncLog.startedAt) < thirtyMinutesAgo) {
      return null; // Too old, probably completed or failed
    }

    return { runId, startedAt: recentSyncLog.startedAt };
  } catch (error) {
    console.error('Error getting recent sync request:', error);
    return null;
  }
};

// GET /api/data-sync/running-status
export const loader = withCorsLoader(async ({ request }: LoaderFunctionArgs) => {
  try {
    // Authenticate with Shopify to ensure only valid app users can check status
    const { session } = await authenticate.admin(request);
    
    // Check our sync log table for recent sync requests
    const recentSync = await getRecentSyncRequest();
    
    if (!recentSync) {
      return json({
        success: true,
        data: {
          hasRunningSync: false,
        },
        timestamp: new Date().toISOString(),
      });
    }

    // Check the actual status in Airflow for this runId
    try {
      const dagRun = await checkDagRunStatus(recentSync.runId);
      
      // If the DAG run is still running or queued, return it
      if (dagRun.state === 'running' || dagRun.state === 'queued') {
        return json({
          success: true,
          data: {
            hasRunningSync: true,
            runId: dagRun.dag_run_id,
            status: dagRun.state,
            startDate: dagRun.start_date,
            executionDate: dagRun.execution_date,
          },
          timestamp: new Date().toISOString(),
        });
      }
    } catch (airflowError) {
      // If we can't reach Airflow or the DAG run doesn't exist,
      // assume it's completed and there's no running sync
      console.warn('Could not check Airflow status for runId:', recentSync.runId, airflowError);
    }

    // No running sync found
    return json({
      success: true,
      data: {
        hasRunningSync: false,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Running status API error:', error);
    
    return json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    }, { status: 500 });
  }
});