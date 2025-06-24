
/**
 * Parse URL parameters into an object
 * @param url - URL to parse
 * @returns Object with URL parameters
 */
export const parseUrlParams = (url: string): Record<string, string> => {
  const params: Record<string, string> = {};
  const queryString = url.split('?')[1];
  
  if (!queryString) return params;
  
  const paramPairs = queryString.split('&');
  
  for (const pair of paramPairs) {
    const [key, value] = pair.split('=');
    if (key && value) {
      params[decodeURIComponent(key)] = decodeURIComponent(value);
    }
  }
  
  return params;
};

/**
 * Get UTM parameters from URL
 * @returns Object with UTM parameters
 */
export const getUtmParams = (): Record<string, string> => {
  const params = parseUrlParams(window.location.href);
  const utmParams: Record<string, string> = {};
  
  // Extract all UTM parameters
  Object.keys(params).forEach(key => {
    if (key.startsWith('utm_')) {
      utmParams[key] = params[key];
    }
  });
  
  return utmParams;
};

/**
 * Get the referrer domain
 * @returns Referrer domain or null if not available
 */
export const getReferrer = (): string | null => {
  if (!document.referrer) return null;
  
  try {
    const url = new URL(document.referrer);
    return url.hostname;
  } catch (e) {
    return null;
  }
};

