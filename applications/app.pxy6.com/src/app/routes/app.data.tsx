import {Page, Layout, Card, BlockStack, Text, Button, InlineStack} from "@shopify/polaris";
import {TitleBar} from "@shopify/app-bridge-react";
import { ActionFunctionArgs, json } from "@remix-run/node"; // For server-side action
import { useFetcher, useNavigation } from "@remix-run/react"; // For client-side interaction
import { useState, useEffect } from "react";

// Helper to create Basic Auth header - this will be called within the action
const getServerSideAirflowAuthHeader = (user: string, pass: string) => {
  const credentials = `${user}:${pass}`;
  // btoa is not available in Node.js server environment by default, use Buffer
  return `Basic ${Buffer.from(credentials).toString('base64')}`;
};


export async function action({ request }: ActionFunctionArgs) {
  // Access environment variables securely within the server-side action
  const AIRFLOW_API_BASE_URL = process.env.AIRFLOW_API_BASE_URL || "http://localhost:8081/api/v1";
  const AIRFLOW_API_USER = process.env.AIRFLOW_API_USER || "admin";
  const AIRFLOW_API_PASSWORD = process.env.AIRFLOW_API_PASSWORD || "admin";

  const formData = await request.formData();
  const actionType = formData.get("actionType");

  if (actionType === "triggerDag") {
    const dagId = formData.get("dagId") as string;
    if (!dagId) {
      return json({ success: false, error: "DAG ID is required." }, { status: 400 });
    }

    const airflowUrl = `${AIRFLOW_API_BASE_URL}/dags/${dagId}/dagRuns`;
    console.log(`Attempting to trigger DAG: ${dagId} at ${airflowUrl}`);

    try {
      const response = await fetch(airflowUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": getServerSideAirflowAuthHeader(AIRFLOW_API_USER, AIRFLOW_API_PASSWORD),
        },
        body: JSON.stringify({
          // Optionally pass configuration to the DAG run
          // conf: { shop_id: "your-shop-id" },
        }),
      });

      console.log(`Airflow API response status for ${dagId}: ${response.status}`);
      const responseData = await response.json();
      console.log(`Airflow API response data for ${dagId}:`, responseData);

      if (!response.ok) {
        return json({ success: false, error: `Failed to trigger DAG ${dagId}. Status: ${response.status}. Message: ${responseData.detail || response.statusText}` }, { status: response.status });
      }
      return json({ success: true, message: `Successfully triggered DAG ${dagId}. Run ID: ${responseData.dag_run_id}` });
    } catch (error: any) {
      console.error(`Error triggering DAG ${dagId}:`, error);
      return json({ success: false, error: `Network or other error triggering DAG ${dagId}: ${error.message}` }, { status: 500 });
    }
  }
  return json({ success: false, error: "Invalid action type." }, { status: 400 });
}


// Use a fallback icon as RefreshMajor is not available
const RefreshIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={15}
    height={15}
    viewBox="0 0 65 65"
    aria-hidden="true"
    focusable="false"
    style={{ display: 'inline', verticalAlign: 'middle' }}
  >
    <g id="Layer_3_copy_2">
      <g fill="currentColor">
        <path
          d="m32.5 4.999c-5.405 0-10.444 1.577-14.699 4.282l-5.75-5.75v16.11h16.11l-6.395-6.395c3.18-1.787 6.834-2.82 10.734-2.82 12.171 0 22.073 9.902 22.073 22.074 0 2.899-0.577 5.664-1.599 8.202l4.738 2.762c1.47-3.363 2.288-7.068 2.288-10.964 0-15.164-12.337-27.501-27.5-27.501z"
        />
        <path
          d="m43.227 51.746c-3.179 1.786-6.826 2.827-10.726 2.827-12.171 0-22.073-9.902-22.073-22.073 0-2.739 0.524-5.35 1.439-7.771l-4.731-2.851c-1.375 3.271-2.136 6.858-2.136 10.622 0 15.164 12.336 27.5 27.5 27.5 5.406 0 10.434-1.584 14.691-4.289l5.758 5.759v-16.112h-16.111l6.389 6.388z"
        />
      </g>
    </g>
  </svg>
);

function DataInsightsSection() {
  const fetcher = useFetcher<typeof action>();
  const navigation = useNavigation();
  const [lastRefreshStatus, setLastRefreshStatus] = useState<string | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<string>("July 26, 2024, 10:35 AM"); // Initial placeholder

  const isLoading = navigation.state !== "idle" && navigation.formAction === "/app/data"; // Check if our specific action is loading

  const handleReloadData = async () => {
    setLastRefreshStatus("Reloading data...");

    // Trigger Past Purchases DAG
    const purchasesFormData = new FormData();
    purchasesFormData.append("actionType", "triggerDag");
    purchasesFormData.append("dagId", "shopify_fetch_past_purchases"); // Ensure this matches your DAG ID
    fetcher.submit(purchasesFormData, { method: "post", action: "/app/data" });
    // No 'await' here, let it run. We'll check fetcher.data for results.

    // Trigger Store Metadata DAG - can be done sequentially or in parallel if backend handles it
    // For simplicity, let's assume we want to show status after the first one,
    // or combine them if the UI needs to reflect both.
    // To trigger both and get combined feedback, the action would need to handle multiple DAG triggers
    // or this client-side logic would need to make two fetcher calls and manage their states.
    // For now, this button press will trigger one DAG via the fetcher.
    // If you want to trigger both, you might need two buttons or a more complex action.
  };

  useEffect(() => {
    if (fetcher.data) {
      if (fetcher.data.success) {
        setLastRefreshStatus(`Success: ${fetcher.data.message}`);
        setLastRefreshTime(new Date().toLocaleString()); // Update time on success
      } else {
        setLastRefreshStatus(`Error: ${fetcher.data.error}`);
      }
    }
  }, [fetcher.data]);

  return (
    <Layout.Section>
      <Card>
        <BlockStack gap="300">
          <InlineStack align="space-between" blockAlign="center" gap="400">
            <div>
              <Text variant="headingMd" as="h3">Data Insights</Text>
              <Text as="p" variant="bodySm" tone="subdued">
                Summary of available data. Click "Reload Purchases" to refresh order data or "Reload Metadata" for catalog info.
              </Text>
            </div>
            <InlineStack gap="200">
              <fetcher.Form method="post" action="/app/data" onSubmit={(e) => setLastRefreshStatus("Reloading purchases...")}>
                <input type="hidden" name="actionType" value="triggerDag" />
                <input type="hidden" name="dagId" value="shopify_fetch_past_purchases" />
                <Button submit icon={<RefreshIcon/>} variant="secondary" loading={isLoading && navigation.formData?.get("dagId") === "shopify_fetch_past_purchases"}>
                  Reload Purchases
                </Button>
              </fetcher.Form>
              <fetcher.Form method="post" action="/app/data" onSubmit={(e) => setLastRefreshStatus("Reloading metadata...")}>
                <input type="hidden" name="actionType" value="triggerDag" />
                <input type="hidden" name="dagId" value="shopify_fetch_store_metadata" />
                <Button submit icon={<RefreshIcon/>} variant="primary" loading={isLoading && navigation.formData?.get("dagId") === "shopify_fetch_store_metadata"}>
                  Reload Metadata
                </Button>
              </fetcher.Form>
            </InlineStack>
          </InlineStack>

          {lastRefreshStatus && (
            <Text as="p" tone={fetcher.data?.success ? "success" : "critical"}>
              {lastRefreshStatus}
            </Text>
          )}

          <div style={{display: 'flex', gap: 32, flexWrap: 'wrap'}}>
            <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
              <Card background="bg-surface-secondary" padding="400">
                <BlockStack gap="100">
                  <Text variant="headingSm" as="h4">Product Catalog</Text>
                  <Text as="p">Products: <b>12,540</b></Text>
                  <Text as="p">Categories: <b>250</b></Text>
                  <Text as="p">Collections: <b>85</b></Text>
                </BlockStack>
              </Card>
            </div>
            <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
              <Card background="bg-surface-secondary" padding="400">
                <BlockStack gap="100">
                  <Text variant="headingSm" as="h4">User Activity</Text>
                  <Text as="p">Total Users: <b>85,320</b></Text>
                  <Text as="p">Purchases: <b>15,789</b></Text>
                </BlockStack>
              </Card>
            </div>
            <div style={{ flex: 1, minWidth: 260, maxWidth: 350 }}>
              <Card background="bg-surface-secondary" padding="400">
                <BlockStack gap="100">
                  <Text variant="headingSm" as="h4">Data Freshness</Text>
                  <Text as="p">Last Refresh:</Text>
                  <Text as="p"><b>July 26, 2024, 10:35 AM</b></Text>
                </BlockStack>
              </Card>
            </div>
          </div>
        </BlockStack>
      </Card>
    </Layout.Section>
  );
}

function HypothesesSection() {
  const hypotheses = [
    {
      image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=facearea&w=400&h=300',
      title: 'Flatters pear-shaped body',
      description: 'This hypothesis suggests recommending clothing that complements a pear-shaped body type.',
      status: 'active'
    },
    {
      image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=facearea&w=400&h=300',
      title: 'Recommend color pops on overcast days',
      description: 'This hypothesis proposes recommending clothing with vibrant colors on overcast days.',
      status: 'active'
    },
    {
      image: 'https://images.unsplash.com/photo-1465101046530-73398c7f28ca?auto=format&fit=facearea&w=400&h=300',
      title: 'Boosts confidence for first dates',
      description: 'This hypothesis aims to recommend clothing that enhances confidence and style for first dates.',
      status: 'waiting'
    },
    {
      image: 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=facearea&w=400&h=300',
      title: 'Enhances style for casual Fridays',
      description: 'This hypothesis suggests recommending stylish yet relaxed clothing suitable for casual Fridays.',
      status: 'waiting'
    }
  ];

  return (
    <Layout.Section>
      <Card>
        <BlockStack gap="300">
          <Text variant="headingMd" as="h3">Hypotheses</Text>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'stretch' }}>
            {hypotheses.map((hypothesis, idx) => (
              <div key={idx} style={{ flex: 1, minWidth: 180, maxWidth: 220, height: '100%', display: 'flex' }}>
                <Card padding="400">
                  <BlockStack gap="200">
                    <img src={hypothesis.image} alt="" style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 8 }} />
                    <Text variant="headingSm" as="h4">{hypothesis.title}</Text>
                    <Text as="p" tone="subdued">{hypothesis.description}</Text>
                    <div style={{
                      display: 'inline-block',
                      padding: '2px 10px',
                      borderRadius: 8,
                      background: hypothesis.status === 'active' ? '#63c199' : '#779fe8',
                      color: 'white',
                      fontWeight: 600,
                      fontSize: 12,
                      marginBottom: 0,
                      width: 'fit-content',
                      marginLeft: 'auto',
                    }}>
                      {hypothesis.status === 'active' ? 'Active' : 'Waiting'}
                    </div>
                  </BlockStack>
                </Card>
              </div>
            ))}
          </div>
        </BlockStack>
      </Card>
    </Layout.Section>
  );
}

function DataDashboard() {
  return (
    <Page>
      <TitleBar title="Data Insights"/>
      <Layout>
        <DataInsightsSection />
        <HypothesesSection />
      </Layout>
    </Page>
  );
}

export default function DataPage() {
  return <DataDashboard/>;
}
