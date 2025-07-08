from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import asyncio
import subprocess
import uvicorn
from typing import Dict, Any

app = FastAPI(title="Test App 1", version="1.0.0")

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database_connected: bool

class DeploymentInfo(BaseModel):
    app_name: str
    version: str
    environment: str
    timestamp: str
    status: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db_connected = await check_database_connection()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "test"),
        database_connected=db_connected
    )

@app.get("/info")
async def get_info():
    """Get application information"""
    return {
        "app_name": "test-app1",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "test"),
        "database_url": os.getenv("DATABASE_URL", "").replace("test_password", "***"),
        "ports": {
            "api": 8000,
            "streamlit": 8501
        }
    }

@app.post("/deploy")
async def simulate_deployment(deployment: DeploymentInfo):
    """Simulate deployment endpoint for testing"""
    # Simulate deployment process
    await asyncio.sleep(1)
    
    return {
        "message": "Deployment simulated successfully",
        "deployment_id": f"deploy-{deployment.app_name}-{deployment.timestamp}",
        "status": "success"
    }

@app.get("/test-database")
async def test_database():
    """Test database connection"""
    try:
        # Simple database connection test
        db_connected = await check_database_connection()
        if db_connected:
            return {"status": "success", "message": "Database connection successful"}
        else:
            raise HTTPException(status_code=500, detail="Database connection failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def check_database_connection():
    """Check if database is accessible"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return False
        
        # Simple check - in real implementation this would use SQLAlchemy
        import psycopg2
        conn = psycopg2.connect(database_url)
        conn.close()
        return True
    except Exception:
        return False

def start_streamlit():
    """Start Streamlit app in background"""
    subprocess.Popen([
        "streamlit", "run", "streamlit_app.py", 
        "--server.port=8501", 
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ])

if __name__ == "__main__":
    # Start Streamlit in background
    start_streamlit()
    
    # Start FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)