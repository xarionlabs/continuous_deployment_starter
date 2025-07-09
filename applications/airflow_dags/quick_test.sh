#!/bin/bash
set -e

echo "🚀 Quick Airflow DAG Test"
echo "========================"

# Build Docker image
echo "Building Docker image..."
docker build -t airflow-dags-quick-test .

# Run quick validation
echo "Running quick validation..."
docker run --rm airflow-dags-quick-test python -c "
import sys
sys.path.insert(0, '/app/src')

print('🔍 Testing DAG imports...')

try:
    from dags.shopify_data_pipeline import dag as pipeline_dag
    print(f'✅ Pipeline DAG: {pipeline_dag.dag_id} - {len(pipeline_dag.tasks)} tasks')
except Exception as e:
    print(f'❌ Pipeline DAG failed: {e}')
    sys.exit(1)

try:
    from dags.shopify_past_purchases import dag as purchases_dag
    print(f'✅ Past Purchases DAG: {purchases_dag.dag_id} - {len(purchases_dag.tasks)} tasks')
except Exception as e:
    print(f'❌ Past Purchases DAG failed: {e}')
    sys.exit(1)

try:
    from dags.shopify_store_metadata import dag as metadata_dag
    print(f'✅ Store Metadata DAG: {metadata_dag.dag_id} - {len(metadata_dag.tasks)} tasks')
except Exception as e:
    print(f'❌ Store Metadata DAG failed: {e}')
    sys.exit(1)

print('🎉 All DAGs loaded successfully!')
"

echo "✅ Quick test completed!"
echo ""
echo "To run full validation:"
echo "./validate_dags.sh"