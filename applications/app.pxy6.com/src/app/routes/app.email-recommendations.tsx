import { useState } from "react";
import { Page, Layout, Card, BlockStack, Text, Button, Select, InlineStack, IndexTable, Badge, TextField } from "@shopify/polaris";
import { TitleBar } from "@shopify/app-bridge-react";

const collections = [
  { label: "None", value: "" },
  { label: "Spring Collection", value: "spring" },
  { label: "Summer Essentials", value: "summer" },
  { label: "Winter Warmers", value: "winter" },
];

const hypotheses = [
  {
    title: "Flatters pear-shaped body",
    description: "Recommending clothing that complements a pear-shaped body type.",
  },
  {
    title: "Recommend color pops on overcast days",
    description: "Recommending clothing with vibrant colors on overcast days.",
  },
  {
    title: "Boosts confidence for first dates",
    description: "Recommending clothing that enhances confidence and style for first dates.",
  },
  {
    title: "Enhances style for casual Fridays",
    description: "Recommending stylish yet relaxed clothing suitable for casual Fridays.",
  },
];

// Dummy users for demonstration
const users = [
  { email: "alice@example.com" },
  { email: "bob@example.com" },
  { email: "carol@example.com" },
];

// Dummy past campaigns data with KPIs
const pastCampaigns = [
  {
    id: '1',
    name: 'Summer Sale',
    status: 'Active',
    collection: 'Summer Essentials',
    ctr: '5%',
    openRate: '25%',
    revenueUplift: '+€8,000',
    avgOrderValue: '€120',
  },
  {
    id: '2',
    name: 'Spring Launch',
    status: 'Completed',
    collection: 'Spring Collection',
    ctr: '7%',
    openRate: '30%',
    revenueUplift: '+€12,000',
    avgOrderValue: '€110',
  },
  {
    id: '3',
    name: 'Winter Warmup',
    status: 'Paused',
    collection: 'Winter Warmers',
    ctr: '4%',
    openRate: '20%',
    revenueUplift: '+€4,500',
    avgOrderValue: '€105',
  },
];

// Download icon SVG for button
const DownloadIcon = () => (
  <svg width="16" height="16" fill="none" viewBox="0 0 16 16">
    <path d="M8 2v8m0 0l3-3m-3 3l-3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <rect x="3" y="13" width="10" height="1" rx="0.5" fill="currentColor" />
  </svg>
);

function generateRecommendationsCSV(selectedCollection: string, utmCampaign: string) {
  const headers = ["Email", "Recommendation", "Collection", "UTM Campaign"];
  const rows = users.map((user, idx) => {
    const hypo = hypotheses[idx % hypotheses.length];
    return [
      user.email,
      `${hypo.title}: ${hypo.description}`,
      selectedCollection ? collections.find(c => c.value === selectedCollection)?.label : "",
      utmCampaign,
    ];
  });
  const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(",")).join("\n");
  return csv;
}

function generateCampaignCSV(campaign: any) {
  // Generate a single-row CSV for the campaign KPIs
  const headers = ["Campaign Name", "Status", "Collection", "Open Rate", "CTR", "Revenue Uplift", "Avg. Order Value"];
  const row = [
    campaign.name,
    campaign.status,
    campaign.collection,
    campaign.openRate,
    campaign.ctr,
    campaign.revenueUplift,
    campaign.avgOrderValue,
  ];
  return [headers, row].map(r => r.map(cell => `"${cell}"`).join(",")).join("\n");
}

export default function EmailRecommendationsPage() {
  const [selectedCollection, setSelectedCollection] = useState("");
  const [utmCampaign, setUtmCampaign] = useState("");
  const [downloading, setDownloading] = useState(false);

  const handleDownload = () => {
    setDownloading(true);
    const csv = generateRecommendationsCSV(selectedCollection, utmCampaign);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "email_recommendations.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setDownloading(false);
  };

  return (
    <Page>
      <TitleBar title="Email Recommendations" />
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text variant="headingMd" as="h3">Email Recommendations Export</Text>
              <Text as="p" variant="bodySm" tone="subdued">
                Generate a CSV of user emails and their recommendations. Optionally select a collection to promote.
              </Text>
              <InlineStack gap="400">
                <Select
                  label="Collection to Promote (optional)"
                  options={collections}
                  value={selectedCollection}
                  onChange={setSelectedCollection}
                />
                <TextField
                  label="UTM Campaign"
                  value={utmCampaign}
                  onChange={setUtmCampaign}
                  autoComplete="off"
                  placeholder="e.g. summer_sale_2025"
                />
              </InlineStack>
              <Button variant="primary" size="medium" loading={downloading} onClick={handleDownload}>
                Download CSV
              </Button>
            </BlockStack>
          </Card>
        </Layout.Section>
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text variant="headingMd" as="h3">Past Campaigns</Text>
              <IndexTable
                resourceName={{ singular: 'campaign', plural: 'campaigns' }}
                itemCount={pastCampaigns.length}
                selectedItemsCount={-1}
                headings={[
                  { title: 'Campaign Name' },
                  { title: 'Status' },
                  { title: 'Collection Promoted' },
                  { title: 'Open Rate' },
                  { title: 'CTR' },
                  { title: 'Revenue Uplift' },
                  { title: 'Avg. Order Value' },
                  { title: 'Download' },
                ]}
                selectable={false}
              >
                {pastCampaigns.map((campaign, idx) => (
                  <IndexTable.Row id={campaign.id} key={campaign.id} position={idx}>
                    <IndexTable.Cell>{campaign.name}</IndexTable.Cell>
                    <IndexTable.Cell>
                      <Badge
                        tone={
                          campaign.status === 'Active' ? 'success' :
                          campaign.status === 'Completed' ? 'info' :
                          campaign.status === 'Paused' ? 'warning' :
                          undefined
                        }
                        progress="complete"
                      >
                        {campaign.status}
                      </Badge>
                    </IndexTable.Cell>
                    <IndexTable.Cell>{campaign.collection}</IndexTable.Cell>
                    <IndexTable.Cell>{campaign.openRate}</IndexTable.Cell>
                    <IndexTable.Cell>{campaign.ctr}</IndexTable.Cell>
                    <IndexTable.Cell>{campaign.revenueUplift}</IndexTable.Cell>
                    <IndexTable.Cell>{campaign.avgOrderValue}</IndexTable.Cell>
                    <IndexTable.Cell>
                      <Button
                        icon={<DownloadIcon />}
                        size="micro"
                        variant="plain"
                        accessibilityLabel={`Download CSV for ${campaign.name}`}
                        onClick={() => {
                          const csv = generateCampaignCSV(campaign);
                          const blob = new Blob([csv], { type: "text/csv" });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `${campaign.name.replace(/\s+/g, '_').toLowerCase()}_campaign.csv`;
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          URL.revokeObjectURL(url);
                        }}
                      />
                    </IndexTable.Cell>
                  </IndexTable.Row>
                ))}
              </IndexTable>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
