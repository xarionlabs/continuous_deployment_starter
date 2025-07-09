import streamlit as st
import os
import requests
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Test App 1 - Streamlit", page_icon="🧪")

st.title("Test App 1 - Streamlit Interface")

# Environment info
st.sidebar.header("Environment Info")
st.sidebar.write(f"Environment: {os.getenv('ENVIRONMENT', 'test')}")
st.sidebar.write(f"Database URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")

# Database connection test
st.header("Database Connection Test")
if st.button("Test Database Connection"):
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            st.success("Database connection successful!")
            st.write(f"PostgreSQL version: {version}")
        else:
            st.error("Database URL not configured")
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")

# API connection test
st.header("API Connection Test")
if st.button("Test API Connection"):
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            health_data = response.json()
            st.success("API connection successful!")
            st.json(health_data)
        else:
            st.error(f"API returned status code: {response.status_code}")
    except Exception as e:
        st.error(f"API connection failed: {str(e)}")

# Deployment simulation
st.header("Deployment Simulation")
col1, col2 = st.columns(2)

with col1:
    app_name = st.text_input("App Name", value="test-app1")
    version = st.text_input("Version", value="1.0.0")

with col2:
    environment = st.selectbox("Environment", ["test", "staging", "production"])
    
if st.button("Simulate Deployment"):
    try:
        deployment_data = {
            "app_name": app_name,
            "version": version,
            "environment": environment,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        response = requests.post("http://localhost:8000/deploy", json=deployment_data)
        if response.status_code == 200:
            result = response.json()
            st.success("Deployment simulated successfully!")
            st.json(result)
        else:
            st.error(f"Deployment failed with status: {response.status_code}")
    except Exception as e:
        st.error(f"Deployment simulation failed: {str(e)}")

# System status
st.header("System Status")
status_col1, status_col2 = st.columns(2)

with status_col1:
    st.metric("Current Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.metric("Environment", os.getenv("ENVIRONMENT", "test"))

with status_col2:
    st.metric("API Port", "8000")
    st.metric("Streamlit Port", "8501")