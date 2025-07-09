// Import whatwg-fetch polyfill for testing
import 'whatwg-fetch';

// Mock the authenticate.webhook function
jest.mock('~/shopify.server', () => ({
  authenticate: {
    webhook: jest.fn().mockImplementation(async (request: Request) => {
      // Get headers from the request
      const headers = new Headers(request.headers);
      const hmac = headers.get('x-shopify-hmac-sha256');
      const topic = headers.get('x-shopify-topic');
      const shop = headers.get('x-shopify-shop-domain') || 'test-shop.myshopify.com';

      // In test environment, we'll only validate that HMAC exists and is not empty
      if (!hmac || typeof hmac !== 'string' || hmac.trim() === '') {
        throw new Error('Invalid HMAC');
      }

      // Parse the request body
      let body;
      try {
        body = await request.json();
      } catch {
        body = {};
      }

      // Return the parsed body with the topic and shop
      return {
        payload: body,
        topic: topic || 'unknown',
        shop,
        session: {}
      };
    })
  }
}));

// Mock the Slack utility
jest.mock('~/utils/slack.server', () => ({
  sendSlackMessage: jest.fn().mockResolvedValue({ ok: true }),
  formatComplianceBlocks: jest.fn().mockReturnValue({
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: 'Test message'
        }
      }
    ]
  })
}));

// Add global test setup here
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();
});
