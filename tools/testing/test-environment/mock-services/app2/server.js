import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from dist directory
app.use(express.static(join(__dirname, 'dist')));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'test',
    timestamp: new Date().toISOString()
  });
});

// API endpoints for testing
app.get('/api/info', (req, res) => {
  res.json({
    app_name: 'test-app2',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'test',
    api_url: process.env.VITE_API_URL || 'http://localhost:8000',
    build_time: new Date().toISOString()
  });
});

app.post('/api/deploy', (req, res) => {
  const { app_name, version, environment } = req.body;
  
  // Simulate deployment
  setTimeout(() => {
    res.json({
      message: 'Frontend deployment simulated successfully',
      deployment_id: `deploy-${app_name}-${Date.now()}`,
      status: 'success',
      timestamp: new Date().toISOString()
    });
  }, 1000);
});

// Serve React app for all other routes
app.get('*', (req, res) => {
  try {
    const indexPath = join(__dirname, 'dist', 'index.html');
    const html = readFileSync(indexPath, 'utf-8');
    res.send(html);
  } catch (error) {
    res.status(500).send('Error serving application');
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Test App 2 server running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'test'}`);
  console.log(`API URL: ${process.env.VITE_API_URL || 'http://localhost:8000'}`);
});