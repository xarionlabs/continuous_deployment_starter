/**
 * Airflow REST API Client
 * 
 * This client provides methods to interact with the Airflow REST API
 * for triggering DAGs, checking status, and retrieving sync history.
 */

interface AirflowConfig {
  baseUrl: string;
  username?: string;
  password?: string;
  timeout?: number;
}

interface JwtResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

interface DagRun {
  dag_id: string;
  dag_run_id: string;
  execution_date: string;
  start_date: string;
  end_date: string | null;
  state: 'queued' | 'running' | 'success' | 'failed' | 'up_for_retry' | 'up_for_reschedule' | 'upstream_failed' | 'skipped' | 'removed' | 'scheduled';
  external_trigger: boolean;
  run_type: 'manual' | 'scheduled' | 'backfill' | 'dataset_triggered';
  conf: Record<string, any>;
  data_interval_start: string;
  data_interval_end: string;
  last_scheduling_decision: string | null;
  run_id: string;
  note: string | null;
}

interface DagRunsResponse {
  dag_runs: DagRun[];
  total_entries: number;
}

interface TriggerDagRequest {
  dag_run_id?: string;
  logical_date?: string;
  conf?: Record<string, any>;
  execution_date?: string;
  replace_microseconds?: boolean;
  reset_dag_runs?: boolean;
  note?: string;
}

interface TaskInstance {
  task_id: string;
  dag_id: string;
  run_id: string;
  execution_date: string;
  start_date: string | null;
  end_date: string | null;
  duration: number | null;
  state: 'none' | 'removed' | 'scheduled' | 'queued' | 'running' | 'success' | 'shutdown' | 'restarting' | 'failed' | 'up_for_retry' | 'up_for_reschedule' | 'upstream_failed' | 'skipped' | 'deferred';
  try_number: number;
  max_tries: number;
  hostname: string;
  unixname: string;
  job_id: number | null;
  pool: string;
  pool_slots: number;
  queue: string;
  priority_weight: number;
  operator: string;
  queued_dttm: string | null;
  pid: number | null;
  executor_config: string;
  note: string | null;
}

interface TaskInstancesResponse {
  task_instances: TaskInstance[];
  total_entries: number;
}

interface SyncMetrics {
  totalProducts: number;
  totalCustomers: number;
  totalOrders: number;
  lastSyncTime: string;
  syncStatus: 'success' | 'failed' | 'running' | 'pending';
  recordsProcessed: number;
  recordsCreated: number;
  recordsUpdated: number;
  errors: string[];
}

interface SyncHistoryEntry {
  runId: string;
  startTime: string;
  endTime: string | null;
  status: string;
  metrics: SyncMetrics;
}

export class AirflowClient {
  private config: AirflowConfig;
  private baseHeaders: Record<string, string>;
  private accessToken: string | null = null;
  private tokenExpiry: Date | null = null;

  constructor(config: AirflowConfig) {
    this.config = {
      timeout: 30000,
      ...config,
    };
    
    // Create base headers
    this.baseHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Get JWT token from Airflow API
   */
  private async getJwtToken(): Promise<string> {
    if (!this.config.username || !this.config.password) {
      throw new Error('Username and password are required for JWT authentication');
    }

    // Check if we have a valid token
    if (this.accessToken && this.tokenExpiry && new Date() < this.tokenExpiry) {
      return this.accessToken;
    }

    // Request new JWT token
    const loginUrl = `${this.config.baseUrl.replace('/api/v2', '')}/auth/token`;
    const response = await fetch(loginUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        username: this.config.username,
        password: this.config.password,
      }),
      signal: AbortSignal.timeout(this.config.timeout!),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`JWT authentication failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const jwtResponse: JwtResponse = await response.json();
    this.accessToken = jwtResponse.access_token;
    
    // Set token expiry (default to 1 hour if not provided)
    const expiresInMs = (jwtResponse.expires_in || 3600) * 1000;
    this.tokenExpiry = new Date(Date.now() + expiresInMs - 60000); // Refresh 1 minute before expiry

    return this.accessToken;
  }

  /**
   * Get authorization headers for requests
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    if (this.config.username && this.config.password) {
      try {
        // Try JWT authentication first
        const token = await this.getJwtToken();
        return {
          'Authorization': `Bearer ${token}`,
        };
      } catch (error) {
        // Fall back to Basic authentication if JWT fails
        console.warn('JWT authentication failed, falling back to Basic auth:', error);
        const credentials = Buffer.from(`${this.config.username}:${this.config.password}`).toString('base64');
        return {
          'Authorization': `Basic ${credentials}`,
        };
      }
    }
    return {};
  }

  /**
   * Make HTTP request to Airflow API
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;
    const authHeaders = await this.getAuthHeaders();
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.baseHeaders,
        ...authHeaders,
        ...options.headers,
      },
      signal: AbortSignal.timeout(this.config.timeout!),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Airflow API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    return response.json();
  }

  /**
   * Test connection to Airflow API
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.makeRequest('/monitor/health');
      return true;
    } catch (error) {
      console.error('Airflow connection test failed:', error);
      return false;
    }
  }

  /**
   * Trigger Shopify data sync DAG
   */
  async triggerDataSync(config: {
    syncMode?: 'full' | 'incremental';
    enableProducts?: boolean;
    enableCustomers?: boolean;
    enableOrders?: boolean;
    note?: string;
    shopDomain?: string;
    accessToken?: string;
    shopId?: string;
  } = {}): Promise<DagRun> {
    const dagId = 'shopify_sync';
    
    const requestBody: TriggerDagRequest = {
      // Let Airflow generate the dag_run_id automatically
      logical_date: new Date().toISOString(),
      conf: {
        sync_mode: config.syncMode || 'incremental',
        enable_products_sync: config.enableProducts !== false,
        enable_customers_sync: config.enableCustomers !== false,
        enable_orders_sync: config.enableOrders !== false,
        // Shop-specific data for multi-tenant support
        shop_domain: config.shopDomain,
        access_token: config.accessToken,
        shop_id: config.shopId,
        triggered_by: 'app_pxy6_com',
        trigger_time: new Date().toISOString(),
      },
      note: config.note || 'Triggered from app.pxy6.com data dashboard',
    };

    return this.makeRequest<DagRun>(`/dags/${dagId}/dagRuns`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  }

  /**
   * Get DAG run status
   */
  async getDagRunStatus(runId: string): Promise<DagRun> {
    const dagId = 'shopify_sync';
    return this.makeRequest<DagRun>(`/dags/${dagId}/dagRuns/${runId}`);
  }

  /**
   * Get DAG run history
   */
  async getDagRunHistory(limit: number = 10): Promise<DagRunsResponse> {
    const dagId = 'shopify_sync';
    const params = new URLSearchParams({
      limit: limit.toString(),
      order_by: '-execution_date',
    });
    
    return this.makeRequest<DagRunsResponse>(`/dags/${dagId}/dagRuns?${params}`);
  }

  /**
   * Get task instances for a DAG run
   */
  async getTaskInstances(runId: string): Promise<TaskInstancesResponse> {
    const dagId = 'shopify_sync';
    return this.makeRequest<TaskInstancesResponse>(`/dags/${dagId}/dagRuns/${runId}/taskInstances`);
  }

  /**
   * Get sync history with enhanced metrics
   */
  async getSyncHistory(limit: number = 10): Promise<SyncHistoryEntry[]> {
    const dagRunsResponse = await this.getDagRunHistory(limit);
    
    const historyEntries: SyncHistoryEntry[] = [];
    
    for (const dagRun of dagRunsResponse.dag_runs) {
      const taskInstances = await this.getTaskInstances(dagRun.run_id);
      
      // Extract metrics from task instances and DAG run configuration
      const metrics: SyncMetrics = {
        totalProducts: 0,
        totalCustomers: 0,
        totalOrders: 0,
        lastSyncTime: dagRun.end_date || dagRun.start_date,
        syncStatus: this.mapDagRunStateToSyncStatus(dagRun.state),
        recordsProcessed: 0,
        recordsCreated: 0,
        recordsUpdated: 0,
        errors: [],
      };

      // Extract error messages from failed tasks
      const failedTasks = taskInstances.task_instances.filter(
        task => task.state === 'failed'
      );
      
      if (failedTasks.length > 0) {
        metrics.errors = failedTasks.map(task => `${task.task_id}: Task failed`);
      }

      historyEntries.push({
        runId: dagRun.run_id,
        startTime: dagRun.start_date,
        endTime: dagRun.end_date,
        status: dagRun.state,
        metrics,
      });
    }
    
    return historyEntries;
  }

  /**
   * Get the latest sync status
   */
  async getLatestSyncStatus(): Promise<SyncHistoryEntry | null> {
    const history = await this.getSyncHistory(1);
    return history.length > 0 ? history[0] : null;
  }

  /**
   * Cancel a running DAG run
   */
  async cancelDagRun(runId: string): Promise<DagRun> {
    const dagId = 'shopify_sync';
    
    return this.makeRequest<DagRun>(`/dags/${dagId}/dagRuns/${runId}`, {
      method: 'PATCH',
      body: JSON.stringify({ state: 'failed' }),
    });
  }

  /**
   * Get DAG information
   */
  async getDagInfo(): Promise<any> {
    const dagId = 'shopify_sync';
    return this.makeRequest(`/dags/${dagId}`);
  }

  /**
   * Map DAG run state to sync status
   */
  private mapDagRunStateToSyncStatus(state: DagRun['state']): SyncMetrics['syncStatus'] {
    switch (state) {
      case 'success':
        return 'success';
      case 'failed':
      case 'upstream_failed':
        return 'failed';
      case 'running':
        return 'running';
      case 'queued':
      case 'scheduled':
        return 'pending';
      default:
        return 'pending';
    }
  }
}

/**
 * Create Airflow client instance
 */
export function createAirflowClient(): AirflowClient {
  const config: AirflowConfig = {
    baseUrl: process.env.AIRFLOW_API_URL || 'http://localhost:8080/api/v2',
    timeout: 30000,
  };
  
  // Only add credentials if they are provided in environment
  if (process.env.AIRFLOW_USERNAME) {
    config.username = process.env.AIRFLOW_USERNAME;
  }
  
  if (process.env.AIRFLOW_PASSWORD) {
    config.password = process.env.AIRFLOW_PASSWORD;
  }

  return new AirflowClient(config);
}

/**
 * Singleton instance for server-side usage
 */
let airflowClientInstance: AirflowClient | null = null;

/**
 * Get or create Airflow client singleton instance
 */
export function getAirflowClient(): AirflowClient {
  if (!airflowClientInstance) {
    airflowClientInstance = createAirflowClient();
  }
  return airflowClientInstance;
}

// All exports are available as named exports