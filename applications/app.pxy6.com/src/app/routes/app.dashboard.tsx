import {Page, Layout, Card, BlockStack, Text, InlineStack} from "@shopify/polaris";
import {TitleBar} from "@shopify/app-bridge-react";

// Add a CSS grid utility for dashboard layout
const dashboardGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
  gap: 24,
  width: '100%',
};

function OverviewSection() {
  return (
    <BlockStack gap="200">
      <Text variant="headingLg" as="h2">Overview</Text>
      <div style={dashboardGridStyle}>
        <Card background="bg-surface-secondary" padding="400">
          <BlockStack gap="100">
            <Text variant="headingSm" as="h4">Traffic Coverage</Text>
            <div style={{ paddingLeft: '5%' }}>
              <Text variant="heading2xl" as="h2">20%</Text>
            </div>
          </BlockStack>
        </Card>
        <Card background="bg-surface-secondary" padding="400">
          <BlockStack gap="100">
            <Text variant="headingSm" as="h4">Revenue Uplift</Text>
            <div style={{ paddingLeft: '5%' }}>
              <InlineStack blockAlign="baseline">
                <Text variant="heading2xl" as="h2">+12%</Text>
                <Text as="dt" tone="subdued" variant="bodySm" breakWord={false}>&nbsp;vs. baseline</Text>
              </InlineStack>
            </div>
          </BlockStack>
        </Card>
        <Card background="bg-surface-secondary" padding="400">
          <BlockStack gap="100">
            <Text variant="headingSm" as="h4">Absolute Revenue Uplift</Text>
            <div style={{ paddingLeft: '5%' }}>
              <Text variant="heading2xl" as="h2">+€24,000</Text>
            </div>
          </BlockStack>
        </Card>
      </div>
    </BlockStack>
  );
}

function PerformanceCard({
  title,
  value,
  subtitle,
  change,
  chartColor,
  chartData = [],
  baselineData = [],
  unit,
}: {
  title: string;
  value: number | string;
  subtitle: string;
  change: string;
  chartColor: string;
  chartData?: number[];
  baselineData?: number[];
  unit?: string;
}) {
  // Responsive SVG: viewBox is fixed, width is 100%, height is auto
  const viewBoxWidth = 120;
  const viewBoxHeight = 54; // 40 for chart, 14 for labels
  const chartHeight = 40;
  const padding = 5;
  const months = ['Mar', 'Apr', 'May', 'Jun'];
  // Use 8 points for 4 months (2 per month)
  const data = chartData.length ? chartData : [35, 32, 34, 36, 33, 37, 35, 38];
  const baseline = baselineData.length ? baselineData : [30, 30, 32, 33, 31, 33, 32, 34];
  const allVals = [...data, ...baseline];
  const maxVal = Math.max(...allVals);
  const minVal = Math.min(...allVals);
  const step = (viewBoxWidth - 2 * padding) / (data.length - 1);
  const points = data.map((v, i) => {
    const y = padding + ((maxVal - v) / (maxVal - minVal || 1)) * (chartHeight - 2 * padding);
    return `${padding + i * step},${y.toFixed(1)}`;
  }).join(' ');
  const baselinePoints = baseline.map((v, i) => {
    const y = padding + ((maxVal - v) / (maxVal - minVal || 1)) * (chartHeight - 2 * padding);
    return `${padding + i * step},${y.toFixed(1)}`;
  }).join(' ');
  // Area fill for uplifted data
  const areaPoints = `${points} ${padding + (data.length - 1) * step},${chartHeight - padding} ${padding},${chartHeight - padding}`;

  return (
    <Card background="bg-surface-secondary" padding="400">
      <BlockStack gap="100">
        <Text variant="headingSm" as="h4">{title}</Text>
        <Text variant="headingXl" as="h2">{unit}{value}</Text>
        <Text as="p" tone="subdued">{subtitle} <span style={{color:'#2ecc71', fontWeight:600}}>{change}</span></Text>
        <svg width="100%" height="auto" viewBox={`-1 0 ${viewBoxWidth} ${viewBoxHeight}`} style={{display:'block'}} preserveAspectRatio="none">
          {/* Area fill under uplifted line */}
          <polygon points={areaPoints} fill="#2f80ed11" />
          {/* Uplifted data line */}
          <polyline
            fill="none"
            stroke={chartColor}
            strokeWidth="2"
            points={points}
          />
          {/* Baseline dashed line */}
          <polyline
            fill="none"
            stroke="#bdbdbd"
            strokeWidth="2"
            strokeDasharray="3,3"
            points={baselinePoints}
          />
          {/* Month labels */}
          {months.map((m, i) => (
            <text
              key={m}
              x={padding + i * 2 * step}
              y={chartHeight + 12}
              textAnchor="middle"
              fontSize="7"
              fill="#444"
            >
              {m}
            </text>
          ))}
        </svg>
      </BlockStack>
    </Card>
  );
}

function PerformanceSection() {
  return (
    <div style={{ width: '100%', marginTop: 32 }}>
      <BlockStack gap="200">
        <Text variant="headingLg" as="h2">Performance</Text>
        <div style={dashboardGridStyle}>
          <PerformanceCard
            title="Average Basket Size"
            value="2.6"
            subtitle="vs. baseline 1.8"
            change="↑ +0.8 (44%)"
            chartColor="#2f80ed"
            unit=""
            chartData={[35, 32, 34, 36, 33, 37, 35, 38]}
            baselineData={[30, 30, 32, 33, 31, 33, 32, 34]}
          />
          <PerformanceCard
            title="Conversion Rate"
            value="12%"
            subtitle="vs. baseline 6%"
            change="↑ +6% (200%)"
            chartColor="#2f80ed"
            unit=""
            chartData={[20, 25, 28, 30, 27, 29, 31, 32]}
            baselineData={[15, 18, 20, 21, 20, 22, 23, 24]}
          />
          <PerformanceCard
            title="Average Order Value"
            value="120"
            subtitle="vs. baseline €107"
            change="↑ +€13 (12%)"
            chartColor="#2f80ed"
            unit="€"
            chartData={[110, 112, 115, 118, 120, 119, 121, 123]}
            baselineData={[100, 104, 107, 108, 106, 108, 109, 110]}
          />
        </div>
      </BlockStack>
    </div>
  );
}

function HypothesesSummarySection() {
  return (
    <BlockStack gap="200">
      <Text variant="headingLg" as="h2">Hypotheses</Text>
      <div style={dashboardGridStyle}>
        <Card background="bg-surface-secondary" padding="400">
          <BlockStack gap="100">
            <Text variant="headingSm" as="h4">Total Run</Text>
            <div style={{ paddingLeft: '5%' }}>
              <Text variant="headingXl" as="h2">250</Text>
            </div>
          </BlockStack>
        </Card>
        <Card background="bg-surface-secondary" padding="400">
          <BlockStack gap="100">
            <Text variant="headingSm" as="h4">Currently Active</Text>
            <div style={{ paddingLeft: '5%' }}>
              <Text variant="headingXl" as="h2">100</Text>
            </div>
          </BlockStack>
        </Card>
        <Card background="bg-surface-secondary" padding="400">
          <BlockStack gap="100">
            <Text variant="headingSm" as="h4">Converted to Rules</Text>
            <div style={{ paddingLeft: '5%' }}>
              <Text variant="headingXl" as="h2">50</Text>
            </div>
          </BlockStack>
        </Card>
      </div>
    </BlockStack>
  );
}

function Dashboard() {
  return (
    <Page>
      <TitleBar title="Dashboard"/>
      <Layout>
        <Layout.Section>
          <BlockStack gap="600">
            <OverviewSection />
            <PerformanceSection />
            <HypothesesSummarySection />
          </BlockStack>
        </Layout.Section>
      </Layout>
    </Page>
  );
}

export default function DashboardPage() {
  return <Dashboard/>;
}
