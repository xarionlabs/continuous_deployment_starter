import { json } from "@remix-run/node";
import type { ActionFunctionArgs } from "@remix-run/node";
import { withCors } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";
import prisma from "../db.server";
import { getAirflowClient } from "../utils/airflow.client";

/**
 * API Routes for Shopify Data Sync
 * 
 * Endpoints:
 * - POST /api/data-sync - Trigger Shopify data sync DAGs
 * - GET /api/data-sync/status/{runId} - Check DAG run status
 */

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

    // Get Airflow client and test connection
    const airflowClient = getAirflowClient();
    const isConnected = await airflowClient.testConnection();
    if (!isConnected) {
      return json({
        success: false,
        error: 'Unable to connect to Airflow service',
      }, { status: 503 });
    }

    // Trigger the DAG with shop-specific data (let Airflow generate the runId)
    const dagRun = await airflowClient.triggerDataSync({
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