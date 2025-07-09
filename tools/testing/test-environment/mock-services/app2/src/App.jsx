import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [appInfo, setAppInfo] = useState(null);
  const [apiHealth, setApiHealth] = useState(null);
  const [deploymentStatus, setDeploymentStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAppInfo();
    fetchApiHealth();
  }, []);

  const fetchAppInfo = async () => {
    try {
      const response = await fetch('/api/info');
      const data = await response.json();
      setAppInfo(data);
    } catch (error) {
      console.error('Failed to fetch app info:', error);
    }
  };

  const fetchApiHealth = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/health`);
      const data = await response.json();
      setApiHealth(data);
    } catch (error) {
      console.error('Failed to fetch API health:', error);
    }
  };

  const simulateDeployment = async () => {
    setLoading(true);
    setDeploymentStatus(null);
    
    try {
      const response = await fetch('/api/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          app_name: 'test-app2',
          version: '1.0.0',
          environment: 'test',
        }),
      });
      
      const data = await response.json();
      setDeploymentStatus(data);
    } catch (error) {
      setDeploymentStatus({ 
        status: 'error', 
        message: error.message 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🧪 Test App 2</h1>
        <p>React/Vite Test Application</p>
      </header>

      <main className="App-main">
        <section className="info-section">
          <h2>Application Information</h2>
          {appInfo ? (
            <div className="info-card">
              <p><strong>App Name:</strong> {appInfo.app_name}</p>
              <p><strong>Version:</strong> {appInfo.version}</p>
              <p><strong>Environment:</strong> {appInfo.environment}</p>
              <p><strong>API URL:</strong> {appInfo.api_url}</p>
              <p><strong>Build Time:</strong> {new Date(appInfo.build_time).toLocaleString()}</p>
            </div>
          ) : (
            <div className="loading">Loading app info...</div>
          )}
        </section>

        <section className="health-section">
          <h2>API Health Status</h2>
          {apiHealth ? (
            <div className={`health-card ${apiHealth.status === 'healthy' ? 'healthy' : 'unhealthy'}`}>
              <p><strong>Status:</strong> {apiHealth.status}</p>
              <p><strong>Version:</strong> {apiHealth.version}</p>
              <p><strong>Environment:</strong> {apiHealth.environment}</p>
              <p><strong>Database:</strong> {apiHealth.database_connected ? '✅ Connected' : '❌ Disconnected'}</p>
              <p><strong>Last Check:</strong> {new Date(apiHealth.timestamp || Date.now()).toLocaleString()}</p>
            </div>
          ) : (
            <div className="health-card unhealthy">
              <p><strong>Status:</strong> API Unavailable</p>
              <p>Cannot connect to backend API</p>
            </div>
          )}
        </section>

        <section className="deployment-section">
          <h2>Deployment Simulation</h2>
          <button 
            onClick={simulateDeployment} 
            disabled={loading}
            className="deploy-button"
          >
            {loading ? 'Simulating Deployment...' : 'Simulate Deployment'}
          </button>
          
          {deploymentStatus && (
            <div className={`deployment-result ${deploymentStatus.status}`}>
              <h3>Deployment Result</h3>
              <p><strong>Status:</strong> {deploymentStatus.status}</p>
              <p><strong>Message:</strong> {deploymentStatus.message}</p>
              {deploymentStatus.deployment_id && (
                <p><strong>Deployment ID:</strong> {deploymentStatus.deployment_id}</p>
              )}
              {deploymentStatus.timestamp && (
                <p><strong>Timestamp:</strong> {new Date(deploymentStatus.timestamp).toLocaleString()}</p>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;