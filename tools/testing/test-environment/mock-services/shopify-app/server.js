import express from 'express';
import { createRequestHandler } from '@remix-run/express';

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.static('public'));
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'test',
    shopify_configured: !!(process.env.SHOPIFY_API_KEY && process.env.SHOPIFY_API_SECRET),
    database_url: process.env.DATABASE_URL ? 'configured' : 'not configured',
    timestamp: new Date().toISOString()
  });
});

// Mock Shopify API endpoints
app.get('/api/shopify/info', (req, res) => {
  res.json({
    app_name: 'test-shopify-app',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'test',
    shopify_api_key: process.env.SHOPIFY_API_KEY || 'test_key',
    shopify_app_url: process.env.SHOPIFY_APP_URL || 'http://localhost:8080',
    database_connected: !!process.env.DATABASE_URL
  });
});

app.post('/api/shopify/webhook', (req, res) => {
  console.log('Received webhook:', req.body);
  res.json({ 
    status: 'success', 
    message: 'Webhook received',
    timestamp: new Date().toISOString()
  });
});

app.get('/api/shopify/orders', (req, res) => {
  // Mock orders data
  res.json({
    orders: [
      {
        id: 'order_001',
        customer: 'Test Customer 1',
        total: 99.99,
        status: 'fulfilled',
        created_at: new Date(Date.now() - 86400000).toISOString()
      },
      {
        id: 'order_002',
        customer: 'Test Customer 2',
        total: 149.99,
        status: 'pending',
        created_at: new Date().toISOString()
      }
    ],
    total_count: 2
  });
});

// Simple homepage instead of full Remix setup
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Test Shopify App</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 40px; }
          .container { max-width: 800px; margin: 0 auto; }
          .card { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }
          .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
          .healthy { background-color: #d4edda; color: #155724; }
          .unhealthy { background-color: #f8d7da; color: #721c24; }
          button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
          button:hover { background: #0056b3; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>🛍️ Test Shopify App</h1>
          <p>Mock Shopify Remix Application for Testing</p>
          
          <div class="card">
            <h2>Application Status</h2>
            <div id="status" class="status">Loading...</div>
            <button onclick="checkStatus()">Refresh Status</button>
          </div>
          
          <div class="card">
            <h2>Mock Shopify Data</h2>
            <div id="orders">Loading orders...</div>
            <button onclick="loadOrders()">Load Orders</button>
          </div>
          
          <div class="card">
            <h2>Webhook Testing</h2>
            <button onclick="testWebhook()">Test Webhook</button>
            <div id="webhook-result"></div>
          </div>
        </div>
        
        <script>
          async function checkStatus() {
            try {
              const response = await fetch('/health');
              const data = await response.json();
              const statusDiv = document.getElementById('status');
              statusDiv.className = 'status ' + (data.status === 'healthy' ? 'healthy' : 'unhealthy');
              statusDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
              const statusDiv = document.getElementById('status');
              statusDiv.className = 'status unhealthy';
              statusDiv.innerHTML = 'Error: ' + error.message;
            }
          }
          
          async function loadOrders() {
            try {
              const response = await fetch('/api/shopify/orders');
              const data = await response.json();
              const ordersDiv = document.getElementById('orders');
              ordersDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
              const ordersDiv = document.getElementById('orders');
              ordersDiv.innerHTML = 'Error: ' + error.message;
            }
          }
          
          async function testWebhook() {
            try {
              const response = await fetch('/api/shopify/webhook', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test: 'webhook', timestamp: new Date().toISOString() })
              });
              const data = await response.json();
              const resultDiv = document.getElementById('webhook-result');
              resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
              const resultDiv = document.getElementById('webhook-result');
              resultDiv.innerHTML = 'Error: ' + error.message;
            }
          }
          
          // Load initial status
          checkStatus();
          loadOrders();
        </script>
      </body>
    </html>
  `);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Test Shopify App server running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'test'}`);
  console.log(`Shopify API Key: ${process.env.SHOPIFY_API_KEY || 'test_key'}`);
  console.log(`Database URL: ${process.env.DATABASE_URL ? 'configured' : 'not configured'}`);
});