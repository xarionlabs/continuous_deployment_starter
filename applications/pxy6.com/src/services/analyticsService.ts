import { getUtmParams, getReferrer } from "@/utils/urlUtils";

// Google Analytics event names
export const GA_EVENTS = {
  PAGE_VIEW: 'page_view',
  BUTTON_CLICK: 'button_click',
  FORM_SUBMIT: 'form_submit',
  SCROLL_DEPTH: 'scroll_depth',
  TIME_ON_PAGE: 'time_on_page',
  FEATURE_VIEW: 'feature_view',
  METRIC_VIEW: 'metric_view',
  WAITLIST_SIGNUP: 'waitlist_signup',
  FOLLOW_UP_COMPLETE: 'follow_up_complete',
  LOI_SUBMITTED: 'loi_submitted',
  SOCIAL_SHARE: 'social_share',
  ERROR_OCCURRED: 'error_occurred',
  HERO_VARIATION_VIEW: 'hero_variation_view',
  AD_VARIANT_VIEW: 'ad_variant_view',
} as const;

// Custom dimensions
export const GA_DIMENSIONS = {
  USER_TYPE: 'user_type',
  FEATURE_INTEREST: 'feature_interest',
  CONVERSION_STAGE: 'conversion_stage',
  ERROR_TYPE: 'error_type',
  HERO_VARIATION: 'hero_variation',
  AD_VARIANT: 'ad_variant',
} as const;

// Custom metrics
export const GA_METRICS = {
  SCROLL_PERCENTAGE: 'scroll_percentage',
  TIME_ON_PAGE: 'time_on_page',
  INTERACTION_COUNT: 'interaction_count',
} as const;

/**
 * Initialize Google Analytics with custom dimensions and metrics
 */
export const initializeGA = () => {
  if (typeof window === 'undefined' || !window.gtag) return;

  // Set custom dimensions
  window.gtag('config', 'G-KSG7XX7SB4', {
    custom_map: {
      dimension1: GA_DIMENSIONS.USER_TYPE,
      dimension2: GA_DIMENSIONS.FEATURE_INTEREST,
      dimension3: GA_DIMENSIONS.CONVERSION_STAGE,
      dimension4: GA_DIMENSIONS.ERROR_TYPE,
      metric1: GA_METRICS.SCROLL_PERCENTAGE,
      metric2: GA_METRICS.TIME_ON_PAGE,
      metric3: GA_METRICS.INTERACTION_COUNT,
    }
  });
};

/**
 * Track page view with enhanced parameters
 */
export const trackPageView = (page: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  const utmParams = getUtmParams();
  const referrer = getReferrer();

  window.gtag('event', GA_EVENTS.PAGE_VIEW, {
    page_path: page,
    page_title: document.title,
    page_location: window.location.href,
    utm_source: utmParams.utm_source,
    utm_medium: utmParams.utm_medium,
    utm_campaign: utmParams.utm_campaign,
    referrer: referrer,
  });
};

/**
 * Track button clicks
 */
export const trackButtonClick = (buttonName: string, buttonLocation: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.BUTTON_CLICK, {
    button_name: buttonName,
    button_location: buttonLocation,
  });
};

/**
 * Track form submissions
 */
export const trackFormSubmit = (formName: string, success: boolean) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.FORM_SUBMIT, {
    form_name: formName,
    success: success,
  });
};

/**
 * Track scroll depth
 */
export const trackScrollDepth = (depth: number) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.SCROLL_DEPTH, {
    scroll_percentage: depth,
  });
};

/**
 * Track feature views
 */
export const trackFeatureView = (featureName: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.FEATURE_VIEW, {
    feature_name: featureName,
  });
};

/**
 * Track metric views
 */
export const trackMetricView = (metricName: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.METRIC_VIEW, {
    metric_name: metricName,
  });
};

/**
 * Track waitlist signup
 */
export const trackWaitlistSignup = (email: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.WAITLIST_SIGNUP, {
    email: email,
  });
};

/**
 * Track follow-up form completion
 */
export const trackFollowUpComplete = (email: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.FOLLOW_UP_COMPLETE, {
    email: email,
  });
};

/**
 * Track LOI submission
 */
export const trackLOISubmission = (email: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.LOI_SUBMITTED, {
    email: email,
  });
};

/**
 * Track social share
 */
export const trackSocialShare = (platform: string, content: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.SOCIAL_SHARE, {
    platform: platform,
    content: content,
  });
};

/**
 * Track errors
 */
export const trackError = (errorType: string, errorMessage: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.ERROR_OCCURRED, {
    error_type: errorType,
    error_message: errorMessage,
  });
};

/**
 * Track hero variation view
 */
export const trackHeroVariationView = (variation: string) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.HERO_VARIATION_VIEW, {
    hero_variation: variation,
    page_location: window.location.href,
  });
};

/**
 * Track ad variant view
 */
export const trackAdVariantView = (variant: string, utmParams: Record<string, string>) => {
  if (typeof window === 'undefined' || !window.gtag) return;

  window.gtag('event', GA_EVENTS.AD_VARIANT_VIEW, {
    ad_variant: variant,
    utm_source: utmParams.utm_source,
    utm_medium: utmParams.utm_medium,
    utm_campaign: utmParams.utm_campaign,
    page_location: window.location.href,
  });
};

// Add TypeScript declarations for gtag
declare global {
  interface Window {
    gtag: (
      command: 'config' | 'event',
      targetId: string,
      config?: {
        [key: string]: any;
      }
    ) => void;
  }
} 