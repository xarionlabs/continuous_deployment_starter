import { loader, action } from '../app/routes/api.data-sync';
import { getAirflowClient } from '../app/utils/airflow.client';
import prisma from '../app/db.server';
import 'whatwg-fetch';

// Mock the Airflow client
jest.mock('../app/utils/airflow.client', () => ({
  getAirflowClient: jest.fn(),
}));

// Mock the database
jest.mock('../app/db.server', () => ({
  __esModule: true,
  default: {},
}));

// Mock the CORS injector
jest.mock('../app/utils/cors.injector', () => ({
  withCors: jest.fn((handler) => handler),
  withCorsLoader: jest.fn((handler) => handler),
}));

describe('API Data Sync Routes', () => {
  let mockAirflowClient: any;

  beforeEach(() => {
    mockAirflowClient = {
      testConnection: jest.fn(),
      triggerDataSync: jest.fn(),
      getDagRunStatus: jest.fn(),
      getTaskInstances: jest.fn(),
      getSyncHistory: jest.fn(),
    };

    (getAirflowClient as jest.Mock).mockReturnValue(mockAirflowClient);

    // Mock prisma with fallback behavior
    (prisma as any).product = {
      count: jest.fn().mockResolvedValue(100),
    };
    (prisma as any).customer = {
      count: jest.fn().mockResolvedValue(50),
    };
    (prisma as any).order = {
      count: jest.fn().mockResolvedValue(75),
      aggregate: jest.fn().mockResolvedValue({
        _sum: { totalPrice: 10000 },
        _avg: { totalPrice: 133.33 },
      }),
    };
    (prisma as any).collection = {
      count: jest.fn().mockResolvedValue(10),
    };
    (prisma as any).orderLineItem = {
      groupBy: jest.fn().mockResolvedValue([
        {
          productId: 'prod-1',
          _count: { productId: 5 },
          _sum: { quantity: 15 },
        },
      ]),
    };
    (prisma as any).syncLog = {
      findFirst: jest.fn().mockResolvedValue({
        id: 'log-1',
        entityType: 'products',
        operation: 'sync',
        status: 'success',
        startedAt: new Date(),
        completedAt: new Date(),
        recordsProcessed: 100,
        recordsCreated: 10,
        recordsUpdated: 90,
      }),
    };
    (prisma as any).syncState = {
      findMany: jest.fn().mockResolvedValue([
        {
          entityType: 'products',
          lastSyncAt: new Date(),
          isActive: true,
          syncVersion: '1.0',
        },
      ]),
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/data-sync', () => {
    it('should trigger data sync successfully', async () => {
      const mockDagRun = {
        run_id: 'test-run-123',
        dag_run_id: 'manual_1234567890',
        state: 'queued',
        execution_date: '2024-01-01T00:00:00Z',
        conf: {
          sync_mode: 'incremental',
          enable_products_sync: true,
          enable_customers_sync: true,
          enable_orders_sync: true,
        },
      };

      mockAirflowClient.testConnection.mockResolvedValue(true);
      mockAirflowClient.triggerDataSync.mockResolvedValue(mockDagRun);

      const request = new Request('http://localhost/api/data-sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          syncMode: 'incremental',
          enableProducts: true,
          enableCustomers: true,
          enableOrders: true,
          note: 'Test sync',
        }),
      });

      const response = await action({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(true);
      expect(result.data.runId).toBe('test-run-123');
      expect(result.data.state).toBe('queued');
      expect(mockAirflowClient.testConnection).toHaveBeenCalled();
      expect(mockAirflowClient.triggerDataSync).toHaveBeenCalledWith({
        syncMode: 'incremental',
        enableProducts: true,
        enableCustomers: true,
        enableOrders: true,
        note: 'Test sync',
      });
    });

    it('should handle connection failure', async () => {
      mockAirflowClient.testConnection.mockResolvedValue(false);

      const request = new Request('http://localhost/api/data-sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      const response = await action({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Unable to connect to Airflow service');
      expect(response.status).toBe(503);
    });

    it('should validate sync mode', async () => {
      const request = new Request('http://localhost/api/data-sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          syncMode: 'invalid',
        }),
      });

      const response = await action({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid sync mode. Must be "full" or "incremental"');
      expect(response.status).toBe(400);
    });

    it('should handle method not allowed', async () => {
      const request = new Request('http://localhost/api/data-sync', {
        method: 'GET',
      });

      const response = await action({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Method not allowed');
      expect(response.status).toBe(405);
    });
  });

  describe('GET /api/data-sync/history', () => {
    it('should return sync history', async () => {
      const mockHistory = [
        {
          runId: 'test-run-123',
          startTime: '2024-01-01T00:00:00Z',
          endTime: '2024-01-01T00:05:00Z',
          status: 'success',
          metrics: {
            totalProducts: 100,
            totalCustomers: 50,
            totalOrders: 75,
            lastSyncTime: '2024-01-01T00:05:00Z',
            syncStatus: 'success',
            recordsProcessed: 100,
            recordsCreated: 10,
            recordsUpdated: 90,
            errors: [],
          },
        },
      ];

      mockAirflowClient.getSyncHistory.mockResolvedValue(mockHistory);

      const request = new Request('http://localhost/api/data-sync/history?limit=5');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockHistory);
      expect(mockAirflowClient.getSyncHistory).toHaveBeenCalledWith(5);
    });

    it('should use default limit', async () => {
      mockAirflowClient.getSyncHistory.mockResolvedValue([]);

      const request = new Request('http://localhost/api/data-sync/history');

      await loader({ request, context: {}, params: {} });

      expect(mockAirflowClient.getSyncHistory).toHaveBeenCalledWith(10);
    });
  });

  describe('GET /api/data-sync/status/{runId}', () => {
    it('should return DAG run status', async () => {
      const mockDagRun = {
        run_id: 'test-run-123',
        state: 'running',
        start_date: '2024-01-01T00:00:00Z',
        end_date: null,
      };

      const mockTaskInstances = {
        task_instances: [
          {
            task_id: 'sync_products',
            state: 'success',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:02:00Z',
          },
          {
            task_id: 'sync_customers',
            state: 'running',
            start_date: '2024-01-01T00:02:00Z',
            end_date: null,
          },
        ],
        total_entries: 2,
      };

      mockAirflowClient.getDagRunStatus.mockResolvedValue(mockDagRun);
      mockAirflowClient.getTaskInstances.mockResolvedValue(mockTaskInstances);

      const request = new Request('http://localhost/api/data-sync/status/test-run-123');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(true);
      expect(result.data.dagRun).toEqual(mockDagRun);
      expect(result.data.taskInstances).toEqual(mockTaskInstances.task_instances);
      expect(result.data.totalTasks).toBe(2);
    });

    it('should handle missing run ID', async () => {
      const request = new Request('http://localhost/api/data-sync/status/');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Run ID is required');
      expect(response.status).toBe(400);
    });
  });

  describe('GET /api/data-sync/metrics', () => {
    it('should return data metrics', async () => {
      const request = new Request('http://localhost/api/data-sync/metrics');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(true);
      expect(result.data).toHaveProperty('catalog');
      expect(result.data.catalog).toHaveProperty('products', 100);
      expect(result.data.catalog).toHaveProperty('customers', 50);
      expect(result.data.catalog).toHaveProperty('orders', 75);
      expect(result.data.catalog).toHaveProperty('collections', 10);
      expect(result.data).toHaveProperty('revenue');
      expect(result.data).toHaveProperty('sync');
      expect(result.data).toHaveProperty('freshness');
    });

    it('should handle database errors gracefully', async () => {
      // Mock database to throw errors
      (prisma as any).product.count.mockRejectedValue(new Error('Database error'));
      (prisma as any).customer.count.mockRejectedValue(new Error('Database error'));
      (prisma as any).order.count.mockRejectedValue(new Error('Database error'));
      (prisma as any).collection.count.mockRejectedValue(new Error('Database error'));

      const request = new Request('http://localhost/api/data-sync/metrics');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(true);
      expect(result.data.catalog).toEqual({
        products: 0,
        customers: 0,
        orders: 0,
        collections: 0,
      });
    });
  });

  describe('Error handling', () => {
    it('should handle Airflow client errors', async () => {
      mockAirflowClient.getSyncHistory.mockRejectedValue(new Error('Airflow connection failed'));

      const request = new Request('http://localhost/api/data-sync/history');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Airflow connection failed');
      expect(response.status).toBe(500);
    });

    it('should handle unknown endpoints', async () => {
      const request = new Request('http://localhost/api/data-sync/unknown');

      const response = await loader({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Endpoint not found');
      expect(response.status).toBe(404);
    });
  });
});