import { validateShopifyHmac } from "./shopify-hmac";
import { sendSlackMessage, formatComplianceBlocks } from "./slack.server";

type WebhookHandlerOptions = {
  request: Request;
};

export async function handleShopifyWebhook({
  request
}: WebhookHandlerOptions) {
  // Check for required headers
  const hmac = request.headers.get('x-shopify-hmac-sha256');
  const topic = request.headers.get('x-shopify-topic');
  const shop = request.headers.get('x-shopify-shop-domain');

  // Return 401 for missing or empty HMAC to match test expectations
  if (!hmac || hmac.trim() === '') {
    return Response.json({ error: 'Invalid HMAC' }, { status: 401 });
  }

  if (!topic || !shop) {
    return Response.json({ error: 'Missing required headers' }, { status: 400 });
  }

  try {
    // Get raw body for HMAC validation
    const rawBody = await request.text();
    const secret = process.env.SHOPIFY_API_SECRET;
    if (!secret) {
      console.error('Shopify API secret not found');
      return Response.json({ error: 'An error occurred' }, { status: 500 });
    }
    const isVerified = validateShopifyHmac(Buffer.from(rawBody, "utf8"), hmac, secret);

    if (!isVerified) {
      console.error('Webhook HMAC validation failed');
      return Response.json({ error: 'Invalid HMAC' }, { status: 401 });
    }

    // Parse the request body
    let payload;
    try {
      payload = JSON.parse(rawBody);
    } catch (parseError) {
      console.error('Failed to parse webhook body:', parseError);
      return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
    }

    console.log(`Received ${topic} webhook for ${shop}`);

    // Send notification to Slack
    try {
      await sendSlackMessage(
        topic,
        formatComplianceBlocks(topic, { ...payload, shop_domain: shop })
      );
    } catch (slackError) {
      console.error('Failed to send Slack notification:', slackError);
      // Continue processing even if Slack fails
    }

    return Response.json({ success: true }, { status: 200 });
  } catch (error) {
    console.error('Webhook processing error:', error);
    return Response.json({
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}
