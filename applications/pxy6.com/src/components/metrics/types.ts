
// Common types for metrics components
export type ThemeColorConfig = {
  light: string;
  dark: string;
};

export type MetricColorsType = {
  basketSize: {
    light: string;
    dark: string;
    baseline: {
      light: string;
      dark: string;
    }
  },
  conversionRate: {
    light: string;
    dark: string;
    baseline: {
      light: string;
      dark: string;
    }
  },
  aov: {
    light: string;
    dark: string;
    baseline: {
      light: string;
      dark: string;
    }
  }
};

export type MetricDataPoint = {
  month: string;
  baseline?: number;
  uplift?: number;
  value?: number;
};

export type MetricCardProps = {
  title: string;
  value: string | number;
  trend: number;
  period: string;
  baseline?: number;
  uplift?: number;
  children?: React.ReactNode;
};

export type ChartProps = {
  data: MetricDataPoint[];
  baselineKey: string;
  upliftKey?: string;
  chartId: string; 
  colorConfig: ThemeColorConfig | string;
  baselineColor: string;
};
