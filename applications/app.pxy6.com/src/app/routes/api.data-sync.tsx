import { json } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import * as airflowClientModule from "../utils/airflow.client";
import { withCors, withCorsLoader } from "../utils/cors.injector";
import prisma from "../db.server";

/**
 * API Routes for Shopify Data Sync
 * 
 * Endpoints:
 * - POST /api/data-sync - Trigger Shopify data sync DAGs
 * - GET /api/data-sync/status/{runId} - Check DAG run status
 * - GET /api/data-sync/history - Get sync history
 * - GET /api/data-sync/metrics - Get current data metrics
 */

// GET /api/data-sync/history
// GET /api/data-sync/status/{runId}
// GET /api/data-sync/metrics
export const loader = withCorsLoader(async ({ request }: LoaderFunctionArgs) => {
  const url = new URL(request.url);
  const pathname = url.pathname;
  const searchParams = url.searchParams;

  try {
    console.log('airflowClientModule:', Object.keys(airflowClientModule));
    console.log('getAirflowClient type:', typeof airflowClientModule.getAirflowClient);
    const airflowClient = airflowClientModule.getAirflowClient();

    // GET /api/data-sync/history
    if (pathname === '/api/data-sync/history') {
      const limit = parseInt(searchParams.get('limit') || '10', 10);
      const history = await airflowClient.getSyncHistory(limit);
      
      return json({
        success: true,
        data: history,
        timestamp: new Date().toISOString(),
      });
    }

    // GET /api/data-sync/status/{runId}
    if (pathname.startsWith('/api/data-sync/status/')) {
      const runId = pathname.split('/').pop();
      
      if (!runId) {
        return json({
          success: false,
          error: 'Run ID is required',
        }, { status: 400 });
      }

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
    }

    // GET /api/data-sync/metrics
    if (pathname === '/api/data-sync/metrics') {
      const metrics = await getShopifyDataMetrics();
      
      return json({
        success: true,
        data: metrics,
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

    console.log('airflowClientModule:', Object.keys(airflowClientModule));
    console.log('getAirflowClient type:', typeof airflowClientModule.getAirflowClient);
    const airflowClient = airflowClientModule.getAirflowClient();

    // Test connection before triggering
    const isConnected = await airflowClient.testConnection();
    if (!isConnected) {
      return json({
        success: false,
        error: 'Unable to connect to Airflow service',
      }, { status: 503 });
    }

    // Trigger the DAG
    const dagRun = await airflowClient.triggerDataSync({
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

/**
 * Get Shopify data metrics from the database
 */
async function getShopifyDataMetrics() {
  try {
    // Get basic counts - use fallback values if Shopify models don't exist yet
    let productsCount = 0;
    let customersCount = 0;
    let ordersCount = 0;
    let collectionsCount = 0;
    let recentOrdersCount = 0;
    let recentCustomersCount = 0;
    
    try {
      const counts = await Promise.all([
        (prisma as any).product?.count() || 0,
        (prisma as any).customer?.count() || 0,
        (prisma as any).order?.count() || 0,
        (prisma as any).collection?.count() || 0,
        (prisma as any).order?.count({
          where: {
            shopifyCreatedAt: {
              gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
            },
          },
        }) || 0,
        (prisma as any).customer?.count({
          where: {
            shopifyCreatedAt: {
              gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // Last 7 days
            },
          },
        }) || 0,
      ]);
      
      [productsCount, customersCount, ordersCount, collectionsCount, recentOrdersCount, recentCustomersCount] = counts;
    } catch (dbError) {
      console.warn('Some Shopify models not available, using fallback values:', dbError);
    }

    // Get revenue metrics with fallback
    let revenueMetrics = { _sum: { totalPrice: 0 }, _avg: { totalPrice: 0 } };
    let topProductDetails: any[] = [];
    let latestSyncLog: any = null;
    let syncStates: any[] = [];
    
    try {
      if ((prisma as any).order) {
        revenueMetrics = await (prisma as any).order.aggregate({
          _sum: {
            totalPrice: true,
          },
          _avg: {
            totalPrice: true,
          },
          where: {
            financialStatus: 'paid',
            cancelled: false,
          },
        });
      }
    } catch (err) {
      console.warn('Revenue metrics not available:', err);
    }

    try {
      if ((prisma as any).orderLineItem) {
        // Get top products by order frequency
        const topProducts = await (prisma as any).orderLineItem.groupBy({
          by: ['productId'],
          _count: {
            productId: true,
          },
          _sum: {
            quantity: true,
          },
          orderBy: {
            _count: {
              productId: 'desc',
            },
          },
          take: 5,
        });

        // Get product details for top products
        topProductDetails = await Promise.all(
          topProducts.map(async (item: any) => {
            if (!item.productId) return null;
            
            try {
              const product = await (prisma as any).product?.findUnique({
                where: { id: item.productId },
                select: {
                  id: true,
                  title: true,
                  handle: true,
                  vendor: true,
                  productType: true,
                },
              });
              
              return {
                ...product,
                orderCount: item._count.productId,
                totalQuantitySold: item._sum.quantity || 0,
              };
            } catch (err) {
              console.warn('Product details not available:', err);
              return null;
            }
          })
        );
        
        topProductDetails = topProductDetails.filter(Boolean);
      }
    } catch (err) {
      console.warn('Top products not available:', err);
    }

    try {
      if ((prisma as any).syncLog) {
        // Get latest sync information
        latestSyncLog = await (prisma as any).syncLog.findFirst({
          orderBy: {
            startedAt: 'desc',
          },
          select: {
            id: true,
            entityType: true,
            operation: true,
            status: true,
            startedAt: true,
            completedAt: true,
            recordsProcessed: true,
            recordsCreated: true,
            recordsUpdated: true,
            errorMessage: true,
          },
        });
      }
    } catch (err) {
      console.warn('Sync log not available:', err);
    }

    try {
      if ((prisma as any).syncState) {
        // Get sync state for all entities
        syncStates = await (prisma as any).syncState.findMany({
          select: {
            entityType: true,
            lastSyncAt: true,
            isActive: true,
            syncVersion: true,
          },
        });
      }
    } catch (err) {
      console.warn('Sync states not available:', err);
    }

    return {
      catalog: {
        products: productsCount,
        customers: customersCount,
        orders: ordersCount,
        collections: collectionsCount,
      },
      recent: {
        ordersLast7Days: recentOrdersCount,
        customersLast7Days: recentCustomersCount,
      },
      revenue: {
        total: revenueMetrics._sum.totalPrice || 0,
        average: revenueMetrics._avg.totalPrice || 0,
      },
      topProducts: topProductDetails.filter(Boolean),
      sync: {
        lastSync: latestSyncLog,
        syncStates,
      },
      freshness: {
        dataAsOf: new Date().toISOString(),
        lastUpdated: syncStates.reduce((latest: Date, state: any) => {
          return state.lastSyncAt > latest ? state.lastSyncAt : latest;
        }, new Date(0)).toISOString(),
      },
    };

  } catch (error) {
    console.error('Failed to get Shopify data metrics:', error);
    throw new Error('Failed to retrieve data metrics');
  }
}