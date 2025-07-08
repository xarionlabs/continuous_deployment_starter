import { AirflowClient, createAirflowClient, getAirflowClient } from '../app/utils/airflow.client';
import 'whatwg-fetch';

// Mock fetch globally
global.fetch = jest.fn();

describe('AirflowClient', () => {
  let client: AirflowClient;

  beforeEach(() => {
    client = new AirflowClient({
      baseUrl: 'http://localhost:8080/api/v1',
      username: 'test',
      password: 'test',
      timeout: 10000,
    });

    // Reset fetch mock
    (fetch as jest.Mock).mockClear();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('constructor', () => {
    it('should initialize with correct configuration', () => {
      expect(client).toBeInstanceOf(AirflowClient);
    });

    it('should set default timeout', () => {
      const defaultClient = new AirflowClient({
        baseUrl: 'http://localhost:8080/api/v1',
        username: 'test',
        password: 'test',
      });
      expect(defaultClient).toBeInstanceOf(AirflowClient);
    });
  });

  describe('testConnection', () => {
    it('should return true for successful connection', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' }),
      });

      const result = await client.testConnection();

      expect(result).toBe(true);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/health',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Basic dGVzdDp0ZXN0',
            'Content-Type': 'application/json',
            Accept: 'application/json',
          }),
        })
      );
    });

    it('should return false for failed connection', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('Error'),
      });

      const result = await client.testConnection();

      expect(result).toBe(false);
    });

    it('should return false for network error', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const result = await client.testConnection();

      expect(result).toBe(false);
    });
  });

  describe('triggerDataSync', () => {
    it('should trigger data sync with default configuration', async () => {
      const mockDagRun = {
        dag_id: 'shopify_sync',
        dag_run_id: 'manual_1234567890',
        run_id: 'test-run-123',
        state: 'queued',
        execution_date: '2024-01-01T00:00:00Z',
        conf: {
          sync_mode: 'incremental',
          enable_products_sync: true,
          enable_customers_sync: true,
          enable_orders_sync: true,
        },
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDagRun),
      });

      const result = await client.triggerDataSync();

      expect(result).toEqual(mockDagRun);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync/dagRuns',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Basic dGVzdDp0ZXN0',
            'Content-Type': 'application/json',
          }),
          body: expect.stringContaining('"sync_mode":"incremental"'),
        })
      );
    });

    it('should trigger data sync with custom configuration', async () => {
      const mockDagRun = {
        dag_id: 'shopify_sync',
        dag_run_id: 'manual_1234567890',
        run_id: 'test-run-123',
        state: 'queued',
        execution_date: '2024-01-01T00:00:00Z',
        conf: {
          sync_mode: 'full',
          enable_products_sync: true,
          enable_customers_sync: false,
          enable_orders_sync: true,
        },
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDagRun),
      });

      const result = await client.triggerDataSync({
        syncMode: 'full',
        enableProducts: true,
        enableCustomers: false,
        enableOrders: true,
        note: 'Custom sync',
      });

      expect(result).toEqual(mockDagRun);
      const fetchCall = (fetch as jest.Mock).mock.calls[0];
      const requestBody = JSON.parse(fetchCall[1].body);
      expect(requestBody.conf.sync_mode).toBe('full');
      expect(requestBody.conf.enable_customers_sync).toBe(false);
      expect(requestBody.note).toBe('Custom sync');
    });

    it('should handle API errors', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: () => Promise.resolve('Invalid request'),
      });

      await expect(client.triggerDataSync()).rejects.toThrow(
        'Airflow API error: 400 Bad Request - Invalid request'
      );
    });
  });

  describe('getDagRunStatus', () => {
    it('should return DAG run status', async () => {
      const mockDagRun = {
        dag_id: 'shopify_sync',
        run_id: 'test-run-123',
        state: 'running',
        start_date: '2024-01-01T00:00:00Z',
        end_date: null,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDagRun),
      });

      const result = await client.getDagRunStatus('test-run-123');

      expect(result).toEqual(mockDagRun);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync/dagRuns/test-run-123',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Basic dGVzdDp0ZXN0',
          }),
        })
      );
    });
  });

  describe('getDagRunHistory', () => {
    it('should return DAG run history with default limit', async () => {
      const mockHistory = {
        dag_runs: [
          {
            dag_id: 'shopify_sync',
            run_id: 'test-run-123',
            state: 'success',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:05:00Z',
          },
        ],
        total_entries: 1,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHistory),
      });

      const result = await client.getDagRunHistory();

      expect(result).toEqual(mockHistory);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync/dagRuns?limit=10&order_by=-execution_date',
        expect.any(Object)
      );
    });

    it('should return DAG run history with custom limit', async () => {
      const mockHistory = {
        dag_runs: [],
        total_entries: 0,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHistory),
      });

      await client.getDagRunHistory(5);

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync/dagRuns?limit=5&order_by=-execution_date',
        expect.any(Object)
      );
    });
  });

  describe('getTaskInstances', () => {
    it('should return task instances', async () => {
      const mockTaskInstances = {
        task_instances: [
          {
            task_id: 'sync_products',
            dag_id: 'shopify_sync',
            run_id: 'test-run-123',
            state: 'success',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:02:00Z',
          },
        ],
        total_entries: 1,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTaskInstances),
      });

      const result = await client.getTaskInstances('test-run-123');

      expect(result).toEqual(mockTaskInstances);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync/dagRuns/test-run-123/taskInstances',
        expect.any(Object)
      );
    });
  });

  describe('getSyncHistory', () => {
    it('should return enhanced sync history', async () => {
      const mockDagRuns = {
        dag_runs: [
          {
            dag_id: 'shopify_sync',
            run_id: 'test-run-123',
            state: 'success',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:05:00Z',
          },
        ],
        total_entries: 1,
      };

      const mockTaskInstances = {
        task_instances: [
          {
            task_id: 'sync_products',
            state: 'success',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:02:00Z',
          },
        ],
        total_entries: 1,
      };

      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockDagRuns),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockTaskInstances),
        });

      const result = await client.getSyncHistory();

      expect(result).toHaveLength(1);
      expect(result[0]).toHaveProperty('runId', 'test-run-123');
      expect(result[0]).toHaveProperty('status', 'success');
      expect(result[0]).toHaveProperty('metrics');
      expect(result[0].metrics).toHaveProperty('syncStatus', 'success');
    });

    it('should handle failed tasks in sync history', async () => {
      const mockDagRuns = {
        dag_runs: [
          {
            dag_id: 'shopify_sync',
            run_id: 'test-run-123',
            state: 'failed',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:05:00Z',
          },
        ],
        total_entries: 1,
      };

      const mockTaskInstances = {
        task_instances: [
          {
            task_id: 'sync_products',
            state: 'failed',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:02:00Z',
          },
        ],
        total_entries: 1,
      };

      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockDagRuns),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockTaskInstances),
        });

      const result = await client.getSyncHistory();

      expect(result[0].metrics.syncStatus).toBe('failed');
      expect(result[0].metrics.errors).toContain('sync_products: Task failed');
    });
  });

  describe('getLatestSyncStatus', () => {
    it('should return latest sync status', async () => {
      const mockDagRuns = {
        dag_runs: [
          {
            dag_id: 'shopify_sync',
            run_id: 'test-run-123',
            state: 'success',
            start_date: '2024-01-01T00:00:00Z',
            end_date: '2024-01-01T00:05:00Z',
          },
        ],
        total_entries: 1,
      };

      const mockTaskInstances = {
        task_instances: [],
        total_entries: 0,
      };

      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockDagRuns),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockTaskInstances),
        });

      const result = await client.getLatestSyncStatus();

      expect(result).toBeTruthy();
      expect(result?.runId).toBe('test-run-123');
    });

    it('should return null when no history', async () => {
      const mockDagRuns = {
        dag_runs: [],
        total_entries: 0,
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDagRuns),
      });

      const result = await client.getLatestSyncStatus();

      expect(result).toBeNull();
    });
  });

  describe('cancelDagRun', () => {
    it('should cancel a DAG run', async () => {
      const mockDagRun = {
        dag_id: 'shopify_sync',
        run_id: 'test-run-123',
        state: 'failed',
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDagRun),
      });

      const result = await client.cancelDagRun('test-run-123');

      expect(result).toEqual(mockDagRun);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync/dagRuns/test-run-123',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ state: 'failed' }),
        })
      );
    });
  });

  describe('getDagInfo', () => {
    it('should return DAG information', async () => {
      const mockDagInfo = {
        dag_id: 'shopify_sync',
        is_active: true,
        is_paused: false,
        description: 'Shopify data synchronization pipeline',
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDagInfo),
      });

      const result = await client.getDagInfo();

      expect(result).toEqual(mockDagInfo);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1/dags/shopify_sync',
        expect.any(Object)
      );
    });
  });

  describe('Factory functions', () => {
    beforeEach(() => {
      // Reset environment variables
      delete process.env.AIRFLOW_API_URL;
      delete process.env.AIRFLOW_USERNAME;
      delete process.env.AIRFLOW_PASSWORD;
    });

    it('should create client with environment variables', () => {
      process.env.AIRFLOW_API_URL = 'http://test:8080/api/v1';
      process.env.AIRFLOW_USERNAME = 'testuser';
      process.env.AIRFLOW_PASSWORD = 'testpass';

      const client = createAirflowClient();

      expect(client).toBeInstanceOf(AirflowClient);
    });

    it('should create client with default values', () => {
      const client = createAirflowClient();

      expect(client).toBeInstanceOf(AirflowClient);
    });

    it('should return singleton instance', () => {
      const client1 = getAirflowClient();
      const client2 = getAirflowClient();

      expect(client1).toBe(client2);
    });
  });

  describe('Error handling', () => {
    it('should handle timeout errors', async () => {
      (fetch as jest.Mock).mockImplementationOnce(() => {
        return new Promise((resolve, reject) => {
          setTimeout(() => {
            reject(new Error('Request timeout'));
          }, 100);
        });
      });

      await expect(client.testConnection()).resolves.toBe(false);
    });

    it('should handle JSON parsing errors', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(client.testConnection()).resolves.toBe(false);
    });
  });
});