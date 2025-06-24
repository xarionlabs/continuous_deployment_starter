import { getUtmParams, getReferrer } from "@/utils/urlUtils";

// Tracking data storage key
const TRACKING_KEY = "pxy6_visitor_source";

// LinkedIn conversion IDs
const LINKEDIN_CONVERSIONS = {
  WAITLIST_SIGNUP: "20998402",
  FOLLOW_UP_COMPLETE: "20998410",
  LOI_SUBMITTED: "20998418",
};

// Extend Window interface to include LinkedIn tracking
declare global {
  interface Window {
    lintrk: (action: string, params: { conversion_id: string }) => void;
  }
}

// Tracking data interface
interface TrackingData {
  firstVisit: string;
  utmParams: Record<string, string>;
  referrer: string | null;
  landingPage: string;
}

/**
 * Track LinkedIn conversion
 */
export const trackLinkedInConversion = (conversionId: string) => {
  if (typeof window !== 'undefined' && window.lintrk) {
    window.lintrk('track', { conversion_id: conversionId });
  }
};

/**
 * Track waitlist signup conversion
 */
export const trackWaitlistSignup = () => {
  trackLinkedInConversion(LINKEDIN_CONVERSIONS.WAITLIST_SIGNUP);
};

/**
 * Track follow-up form completion
 */
export const trackFollowUpComplete = () => {
  trackLinkedInConversion(LINKEDIN_CONVERSIONS.FOLLOW_UP_COMPLETE);
};

/**
 * Track LOI submission
 */
export const trackLOISubmission = () => {
  trackLinkedInConversion(LINKEDIN_CONVERSIONS.LOI_SUBMITTED);
};

/**
 * Initialize tracking when the user first visits the site
 */
export const initializeTracking = (): TrackingData => {
  // Check if tracking data already exists
  const existingData = getTrackingData();
  if (existingData) {
    return existingData;
  }
  
  // Create new tracking data
  const trackingData: TrackingData = {
    firstVisit: new Date().toISOString(),
    utmParams: getUtmParams(),
    referrer: getReferrer(),
    landingPage: window.location.pathname,
  };
  
  // Store the tracking data
  localStorage.setItem(TRACKING_KEY, JSON.stringify(trackingData));
  
  return trackingData;
};

/**
 * Get tracking data from storage
 */
export const getTrackingData = (): TrackingData | null => {
  const data = localStorage.getItem(TRACKING_KEY);
  if (!data) return null;
  
  try {
    return JSON.parse(data) as TrackingData;
  } catch (e) {
    return null;
  }
};

/**
 * Get source summary for analytics
 */
export const getSourceSummary = (): string => {
  const data = getTrackingData();
  if (!data) return "direct";
  
  // Check for UTM source first (highest priority)
  if (data.utmParams.utm_source) {
    const utmParams = Object.entries(data.utmParams)
      .filter(([key]) => key.startsWith('utm_'))
      .map(([key, value]) => `${key}=${value}`)
      .join('&');
    return utmParams;
  }
  
  // Use referrer if available
  if (data.referrer) {
    return `ref_${data.referrer}`;
  }
  
  // Default to direct
  return "direct";
};

