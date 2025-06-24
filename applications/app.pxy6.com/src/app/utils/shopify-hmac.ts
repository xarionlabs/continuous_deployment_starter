import * as crypto from 'crypto';

/**
 * Validates a Shopify webhook HMAC signature.
 *
 * @param rawBody Buffer or string of the raw request body
 * @param hmacHeader The value of the X-Shopify-Hmac-SHA256 header
 * @param secret The Shopify app secret (from env)
 * @returns boolean
 */
export function validateShopifyHmac(rawBody: Buffer | string, hmacHeader: string | null | undefined, secret: string): boolean {
  if (!hmacHeader || !secret) return false;
  const digest = crypto
    .createHmac("sha256", secret)
    .update(typeof rawBody === "string" ? Buffer.from(rawBody, "utf8") : rawBody)
    .digest("base64");
  try {
    return crypto.timingSafeEqual(Buffer.from(digest), Buffer.from(hmacHeader));
  } catch {
    return false;
  }
}
