import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { withCorsLoader } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";
import prisma from "../db.server";
import { getAirflowClient } from "../utils/airflow.server";

/**
 * API Route for Checking Running Sync Status
 * 
 * Endpoint:
 * - GET /api/data-sync/running-status - Check if there are any running/queued DAG runs
 */

// Status checking for running DAG runs

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
    await authenticate.admin(request);
    
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
      const airflowClient = getAirflowClient();
      const dagRun = await airflowClient.getDagRunStatus(recentSync.runId);
      
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