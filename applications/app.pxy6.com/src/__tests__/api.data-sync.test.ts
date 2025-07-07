import { action } from '../app/routes/api.data-sync';
import 'whatwg-fetch';

// Mock the CORS injector
jest.mock('../app/utils/cors.injector', () => ({
  withCors: jest.fn((handler) => handler),
  withCorsLoader: jest.fn((handler) => handler),
}));

describe('API Data Sync Routes', () => {
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
  });
});