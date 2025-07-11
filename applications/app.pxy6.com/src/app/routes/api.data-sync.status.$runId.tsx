import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { withCorsLoader } from "../utils/cors.injector";
import { authenticate } from "../shopify.server";
import { getAirflowClient } from "../utils/airflow.server";

/**
 * API Route for Checking DAG Run Status
 * 
 * Endpoint:
 * - GET /api/data-sync/status/{runId} - Check DAG run status
 */

// DAG run status checking endpoint

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

    const airflowClient = getAirflowClient();
    const dagRun = await airflowClient.getDagRunStatus(runId);
    const taskInstances = await airflowClient.getTaskInstances(runId);
    
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