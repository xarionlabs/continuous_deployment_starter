import { action } from '../app/routes/api.data-sync';
import 'whatwg-fetch';

// Mock the CORS injector
jest.mock('../app/utils/cors.injector', () => ({
  withCors: jest.fn((handler) => handler),
  withCorsLoader: jest.fn((handler) => handler),
}));

// Mock the Shopify authenticate
jest.mock('../app/shopify.server', () => ({
  authenticate: {
    admin: jest.fn(() => Promise.resolve({
      session: {
        shop: 'test-shop.myshopify.com',
        accessToken: 'shpat_test123',
      },
    })),
  },
}));

// Mock fetch for Airflow requests
global.fetch = jest.fn();

describe('API Data Sync Routes', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  describe('POST /api/data-sync', () => {
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
      expect(result.error).toContain('Invalid sync mode');
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

    it('should trigger data sync with shop data', async () => {
      // Mock successful Airflow connection test (using AirflowClient)
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ status: 'healthy' }),
        })
        // Mock successful DAG trigger
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            dag_run_id: 'test-run-123',
            dag_id: 'shopify_sync',
            run_id: 'test-run-123',
            state: 'queued',
            execution_date: '2024-01-01T00:00:00Z',
            start_date: '2024-01-01T00:00:00Z',
            end_date: null,
            external_trigger: true,
            run_type: 'manual',
            conf: {
              shop_domain: 'test-shop',
              access_token: 'shpat_test123',
              sync_mode: 'incremental',
            },
            data_interval_start: '2024-01-01T00:00:00Z',
            data_interval_end: '2024-01-01T00:00:00Z',
            last_scheduling_decision: null,
            note: 'Triggered from app.pxy6.com data dashboard',
          }),
        });

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
        }),
      });

      const response = await action({ request, context: {}, params: {} });
      const result = await response.json();

      expect(result.success).toBe(true);
      expect(result.data.runId).toBe('test-run-123');
      expect(response.status).toBe(200);

      // Verify shop data was passed to Airflow (DAG trigger is the 2nd call after health check)
      const dagTriggerCall = (fetch as jest.Mock).mock.calls[1];
      const requestBody = JSON.parse(dagTriggerCall[1].body);
      expect(requestBody.conf.shop_domain).toBe('test-shop');
      expect(requestBody.conf.access_token).toBe('shpat_test123');
    });
  });
});