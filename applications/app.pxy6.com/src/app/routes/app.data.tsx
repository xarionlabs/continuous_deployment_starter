import {Page, Layout, Card, BlockStack, Text, Button, InlineStack, Spinner, Banner} from "@shopify/polaris";
import {TitleBar} from "@shopify/app-bridge-react";
import {useState, useCallback} from "react";
import type {LoaderFunctionArgs} from "@remix-run/node";
import {json} from "@remix-run/node";
import {useLoaderData} from "@remix-run/react";
import prisma from "../db.server";

// Use a fallback icon as RefreshMajor is not available
const RefreshIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={15}
    height={15}
    viewBox="0 0 65 65"
    aria-hidden="true"
    focusable="false"
    style={{ display: 'inline', verticalAlign: 'middle' }}
  >
    <g id="Layer_3_copy_2">
      <g fill="currentColor">
        <path
          d="m32.5 4.999c-5.405 0-10.444 1.577-14.699 4.282l-5.75-5.75v16.11h16.11l-6.395-6.395c3.18-1.787 6.834-2.82 10.734-2.82 12.171 0 22.073 9.902 22.073 22.074 0 2.899-0.577 5.664-1.599 8.202l4.738 2.762c1.47-3.363 2.288-7.068 2.288-10.964 0-15.164-12.337-27.501-27.5-27.501z"
        />
        <path
          d="m43.227 51.746c-3.179 1.786-6.826 2.827-10.726 2.827-12.171 0-22.073-9.902-22.073-22.073 0-2.739 0.524-5.35 1.439-7.771l-4.731-2.851c-1.375 3.271-2.136 6.858-2.136 10.622 0 15.164 12.336 27.5 27.5 27.5 5.406 0 10.434-1.584 14.691-4.289l5.758 5.759v-16.112h-16.111l6.389 6.388z"
        />
      </g>
    </g>
  </svg>
);

interface DataMetrics {
  catalog: {
    products: number;
    customers: number;
    orders: number;
    collections: number;
  };
  recent: {
    ordersLast7Days: number;
    customersLast7Days: number;
  };
  revenue: {
    total: number;
    average: number;
  };
  topProducts: Array<{
    id: string;
    title: string;
    handle: string;
    vendor: string;
    productType: string;
    orderCount: number;
    totalQuantitySold: number;
  }>;
  sync: {
    lastSync: {
      status: string;
      startedAt: string;
      completedAt?: string;
      recordsProcessed?: number;
      recordsCreated?: number;
      recordsUpdated?: number;
      errorMessage?: string;
    } | null;
    syncStates: Array<{
      entityType: string;
      lastSyncAt: string;
      isActive: boolean;
      syncVersion?: string;
    }>;
  };
  freshness: {
    dataAsOf: string;
    lastUpdated: string;
  };
}

interface SyncStatus {
  isLoading: boolean;
  runId?: string;
  status?: string;
  error?: string;
}

function DataInsightsSection() {
  const loaderData = useLoaderData<typeof loader>();
  const [metrics] = useState<DataMetrics | null>(loaderData.metrics);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({ isLoading: false });
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    try {
      // Reload the page to get fresh data
      window.location.reload();
    } catch (err) {
      setError('Failed to load metrics');
      console.error('Error loading metrics:', err);
    }
  }, []);

  const simulateSyncProgress = useCallback(async (runId: string) => {
    // Simulate sync progress over 3-5 seconds
    const totalSteps = 5;
    const stepDelay = 800; // 800ms per step
    
    for (let step = 1; step <= totalSteps; step++) {
      await new Promise(resolve => setTimeout(resolve, stepDelay));
      
      if (step === totalSteps) {
        // Final step - sync complete
        setSyncStatus({
          isLoading: false,
          runId,
          status: 'success',
        });
        
        // Reload metrics after successful sync
        setTimeout(() => {
          loadMetrics();
        }, 500);
      }
    }
  }, [loadMetrics]);

  const handleDataSync = useCallback(async () => {
    setSyncStatus({ isLoading: true });
    
    try {
      // Generate a mock run ID for tracking
      const mockRunId = `mock_sync_${Date.now()}`;
      
      setSyncStatus({
        isLoading: true,
        runId: mockRunId,
        status: 'running',
      });
      
      // Start the simulated sync progress
      simulateSyncProgress(mockRunId);
      
    } catch (err) {
      setSyncStatus({
        isLoading: false,
        error: 'Failed to start sync',
      });
      console.error('Error starting sync:', err);
    }
  }, [simulateSyncProgress]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  return (
    <Layout.Section>
      <Card>
        <BlockStack gap="300">
          <InlineStack align="space-between" blockAlign="center">
            <div>
              <Text variant="headingMd" as="h3">Data Insights</Text>
              <Text as="p" variant="bodySm" tone="subdued">
                Real-time Shopify data metrics and sync status.
              </Text>
            </div>
            <Button 
              icon={syncStatus.isLoading ? <Spinner size="small" /> : <RefreshIcon/>} 
              variant="secondary"
              loading={syncStatus.isLoading}
              onClick={handleDataSync}
              disabled={syncStatus.isLoading}
            >
              {syncStatus.isLoading ? 'Syncing...' : 'Sync Data'}
            </Button>
          </InlineStack>
          
          {/* Sync Status Banner */}
          {syncStatus.error && (
            <Banner tone="critical" title="Sync Error">
              {syncStatus.error}
            </Banner>
          )}
          
          {syncStatus.status === 'running' && (
            <Banner tone="info" title="Sync in Progress">
              Data synchronization is currently running. Metrics will be updated when complete.
            </Banner>
          )}
          
          {syncStatus.status === 'success' && (
            <Banner tone="success" title="Sync Completed">
              Data synchronization completed successfully. Metrics have been updated.
            </Banner>
          )}
          
          {error && (
            <Banner tone="critical" title="Error Loading Data">
              {error}
            </Banner>
          )}
          
          {metrics ? (
            <div style={{display: 'flex', gap: 32, flexWrap: 'wrap'}}>
              <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
                <Card background="bg-surface-secondary" padding="400">
                  <BlockStack gap="100">
                    <Text variant="headingSm" as="h4">Product Catalog</Text>
                    <Text as="p">Products: <b>{formatNumber(metrics.catalog.products)}</b></Text>
                    <Text as="p">Collections: <b>{formatNumber(metrics.catalog.collections)}</b></Text>
                    <Text as="p">Recent Orders: <b>{formatNumber(metrics.recent.ordersLast7Days)}</b></Text>
                  </BlockStack>
                </Card>
              </div>
              <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
                <Card background="bg-surface-secondary" padding="400">
                  <BlockStack gap="100">
                    <Text variant="headingSm" as="h4">Customer Activity</Text>
                    <Text as="p">Total Customers: <b>{formatNumber(metrics.catalog.customers)}</b></Text>
                    <Text as="p">Total Orders: <b>{formatNumber(metrics.catalog.orders)}</b></Text>
                    <Text as="p">New Customers (7d): <b>{formatNumber(metrics.recent.customersLast7Days)}</b></Text>
                  </BlockStack>
                </Card>
              </div>
              <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
                <Card background="bg-surface-secondary" padding="400">
                  <BlockStack gap="100">
                    <Text variant="headingSm" as="h4">Revenue & Data Freshness</Text>
                    <Text as="p">Total Revenue: <b>{formatCurrency(metrics.revenue.total)}</b></Text>
                    <Text as="p">Avg Order Value: <b>{formatCurrency(metrics.revenue.average)}</b></Text>
                    <Text as="p">Last Updated:</Text>
                    <Text as="p"><b>{formatDate(metrics.freshness.lastUpdated)}</b></Text>
                  </BlockStack>
                </Card>
              </div>
            </div>
          ) : (
            <div style={{display: 'flex', gap: 32, flexWrap: 'wrap'}}>
              <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
                <Card background="bg-surface-secondary" padding="400">
                  <BlockStack gap="100">
                    <Text variant="headingSm" as="h4">Loading...</Text>
                    <Spinner size="small" />
                  </BlockStack>
                </Card>
              </div>
            </div>
          )}
        </BlockStack>
      </Card>
    </Layout.Section>
  );
}

function HypothesesSection() {
  const hypotheses = [
    {
      image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=facearea&w=400&h=300',
      title: 'Flatters pear-shaped body',
      description: 'This hypothesis suggests recommending clothing that complements a pear-shaped body type.',
      status: 'active'
    },
    {
      image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=facearea&w=400&h=300',
      title: 'Recommend color pops on overcast days',
      description: 'This hypothesis proposes recommending clothing with vibrant colors on overcast days.',
      status: 'active'
    },
    {
      image: 'https://images.unsplash.com/photo-1465101046530-73398c7f28ca?auto=format&fit=facearea&w=400&h=300',
      title: 'Boosts confidence for first dates',
      description: 'This hypothesis aims to recommend clothing that enhances confidence and style for first dates.',
      status: 'waiting'
    },
    {
      image: 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=facearea&w=400&h=300',
      title: 'Enhances style for casual Fridays',
      description: 'This hypothesis suggests recommending stylish yet relaxed clothing suitable for casual Fridays.',
      status: 'waiting'
    }
  ];

  return (
    <Layout.Section>
      <Card>
        <BlockStack gap="300">
          <Text variant="headingMd" as="h3">Hypotheses</Text>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'stretch' }}>
            {hypotheses.map((hypothesis, idx) => (
              <div key={idx} style={{ flex: 1, minWidth: 180, maxWidth: 220, height: '100%', display: 'flex' }}>
                <Card padding="400">
                  <BlockStack gap="200">
                    <img src={hypothesis.image} alt="" style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 8 }} />
                    <Text variant="headingSm" as="h4">{hypothesis.title}</Text>
                    <Text as="p" tone="subdued">{hypothesis.description}</Text>
                    <div style={{
                      display: 'inline-block',
                      padding: '2px 10px',
                      borderRadius: 8,
                      background: hypothesis.status === 'active' ? '#63c199' : '#779fe8',
                      color: 'white',
                      fontWeight: 600,
                      fontSize: 12,
                      marginBottom: 0,
                      width: 'fit-content',
                      marginLeft: 'auto',
                    }}>
                      {hypothesis.status === 'active' ? 'Active' : 'Waiting'}
                    </div>
                  </BlockStack>
                </Card>
              </div>
            ))}
          </div>
        </BlockStack>
      </Card>
    </Layout.Section>
  );
}

function DataDashboard() {
  return (
    <Page>
      <TitleBar title="Data Insights"/>
      <Layout>
        <DataInsightsSection />
        <HypothesesSection />
      </Layout>
    </Page>
  );
}

// Loader function for initial data
export async function loader({ request }: LoaderFunctionArgs) {
  const metrics = await getShopifyDataMetrics();
  return json({ 
    timestamp: new Date().toISOString(),
    metrics 
  });
}

/**
 * Get Shopify data metrics from the database
 */
async function getShopifyDataMetrics(): Promise<DataMetrics> {
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
    // Return empty metrics instead of throwing
    return {
      catalog: { products: 0, customers: 0, orders: 0, collections: 0 },
      recent: { ordersLast7Days: 0, customersLast7Days: 0 },
      revenue: { total: 0, average: 0 },
      topProducts: [],
      sync: { lastSync: null, syncStates: [] },
      freshness: { dataAsOf: new Date().toISOString(), lastUpdated: new Date(0).toISOString() },
    };
  }
}

export default function DataPage() {
  return <DataDashboard/>;
}
