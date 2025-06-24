import { useEffect, useRef } from 'react';
import { trackScrollDepth, trackPageView } from '@/services/analyticsService';

export const useAnalytics = (page: string) => {
  const startTime = useRef(Date.now());
  const lastScrollDepth = useRef(0);

  useEffect(() => {
    // Track initial page view
    trackPageView(page);

    // Track scroll depth
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight;
      const winHeight = window.innerHeight;
      const scrollPercent = (scrollTop / (docHeight - winHeight)) * 100;
      
      // Only track when user scrolls past certain thresholds
      const thresholds = [25, 50, 75, 90];
      const currentThreshold = thresholds.find(t => scrollPercent >= t && lastScrollDepth.current < t);
      
      if (currentThreshold) {
        trackScrollDepth(currentThreshold);
        lastScrollDepth.current = currentThreshold;
      }
    };

    // Track time on page
    const timeInterval = setInterval(() => {
      const timeSpent = Math.floor((Date.now() - startTime.current) / 1000);
      if (timeSpent % 30 === 0) { // Track every 30 seconds
        window.gtag?.('event', 'time_on_page', {
          time_spent: timeSpent,
          page: page,
        });
      }
    }, 1000);

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      clearInterval(timeInterval);
    };
  }, [page]);
}; 