import { json } from "@remix-run/node";

type SlackMessage = {
  text: string;
  [key: string]: any;
};

export async function sendSlackMessage(message: string, blocks?: any[]) {
  const webhookUrl = process.env.SLACK_WEBHOOK_URL;

  if (!webhookUrl) {
    console.warn('SLACK_WEBHOOK_URL is not set. Cannot send message to Slack.');
    return null;
  }

  const payload: SlackMessage = {
    text: message,
  };

  if (blocks && blocks.length > 0) {
    payload.blocks = blocks;
  }

  try {
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Slack API error: ${response.statusText}`);
    }

    return await response.text();
  } catch (error) {
    console.error('Error sending message to Slack:', error);
    return null;
  }
}

export function formatComplianceMessage(topic: string, payload: any): string {
  const { shop_domain } = payload;
  return `ℹ️ Webhook received for topic ${topic} for ${shop_domain}`;
}

export function formatComplianceBlocks(topic: string, payload: any) {
  const { shop_domain, shop_id, ...rest } = payload;

  return [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*${formatComplianceMessage(topic, payload)}*`,
      },
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Shop:*\\n${shop_domain}`,
        },
      ],
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: '```' + JSON.stringify(rest, null, 2) + '```',
      },
    },
  ];
}
