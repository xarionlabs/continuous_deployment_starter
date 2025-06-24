import React, { useEffect } from "react";
import { MetricCard } from "./metrics/MetricCard";
import { BasketSizeChart } from "./metrics/BasketSizeChart";
import { ConversionRateChart } from "./metrics/ConversionRateChart";
import { AOVChart } from "./metrics/AOVChart";
import { basketSizeData, conversionRateData, aovData, metricColors } from "./metrics/MetricsData";
import { trackMetricView } from "@/services/analyticsService";

export function MetricsDashboard() {
  const getCurrentTheme = () => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    }
    return 'light';
  };

  // Get the current theme for coloring
  const theme = getCurrentTheme() as "light" | "dark";

  // Track metric views when component mounts
  useEffect(() => {
    trackMetricView('basket_size');
    trackMetricView('conversion_rate');
    trackMetricView('average_order_value');
  }, []);
  
  return (
    <div className="space-y-8 w-full">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard Metrics</h2>
        <p className="text-muted-foreground">
          Illustrative key performance indicators showing expected improvements with our application.
        </p>
      </div>
      
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 w-full">
        {/* Average Basket Size Metric */}
        <MetricCard 
          title="Average Basket Size" 
          value="2.7 items" 
          trend={8.2} 
          period="last month"
          baseline={1.9}
          uplift={2.7}
        >
          <BasketSizeChart 
            data={basketSizeData} 
            theme={theme} 
            colors={metricColors.basketSize}
          />
        </MetricCard>

        {/* Conversion Rate */}
        <MetricCard 
          title="Conversion Rate" 
          value="7.4%" 
          trend={221.7} 
          period="last month"
          baseline={2.3}
          uplift={7.4}
        >
          <ConversionRateChart 
            data={conversionRateData} 
            theme={theme} 
            colors={metricColors.conversionRate}
          />
        </MetricCard>

        {/* Average Order Value */}
        <MetricCard 
          title="Average Order Value" 
          value="€88" 
          trend={8.2} 
          period="last month"
          baseline={69}
          uplift={88}
        >
          <AOVChart 
            data={aovData} 
            theme={theme} 
            colors={metricColors.aov}
          />
        </MetricCard>
      </div>
    </div>
  );
}
