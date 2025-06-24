// Sample data for metrics dashboard
export const basketSizeData = [
  { month: 'Jan', baseline: 1.8, uplift: 2.2 },
  { month: 'Feb', baseline: 1.9, uplift: 2.3 },
  { month: 'Mar', baseline: 1.8, uplift: 2.4 },
  { month: 'Apr', baseline: 1.9, uplift: 2.5 },
  { month: 'May', baseline: 1.8, uplift: 2.6 },
  { month: 'Jun', baseline: 1.9, uplift: 2.7 },
];

export const conversionRateData = [
  { month: 'Jan', baseline: 2.2, uplift: 3.1 },
  { month: 'Feb', baseline: 2.4, uplift: 4.3 },
  { month: 'Mar', baseline: 2.1, uplift: 5.2 },
  { month: 'Apr', baseline: 2.5, uplift: 5.7 },
  { month: 'May', baseline: 2.3, uplift: 6.8 },
  { month: 'Jun', baseline: 2.4, uplift: 7.4 },
];

export const sessionDurationData = [
  { month: 'Jan', value: 2.1 },
  { month: 'Feb', value: 2.2 },
  { month: 'Mar', value: 2.3 },
  { month: 'Apr', value: 2.4 },
  { month: 'May', value: 2.5 },
  { month: 'Jun', value: 2.5 },
];

export const aovData = [
  { month: 'Jan', baseline: 65, uplift: 78 },
  { month: 'Feb', baseline: 67, uplift: 80 },
  { month: 'Mar', baseline: 66, uplift: 82 },
  { month: 'Apr', baseline: 68, uplift: 84 },
  { month: 'May', baseline: 67, uplift: 86 },
  { month: 'Jun', baseline: 69, uplift: 88 },
];

// Chart colors with proper color theming
export const metricColors = {
  basketSize: {
    light: "#10b981", // emerald-500
    dark: "#34d399",  // emerald-400 for dark mode
    baseline: {
      light: "#94a3b8", // slate-400
      dark: "#64748b",  // slate-500 for dark mode
    }
  },
  conversionRate: {
    light: "#10b981", // emerald-500
    dark: "#34d399",  // emerald-400 for dark mode
    baseline: {
      light: "#94a3b8", // slate-400
      dark: "#64748b",  // slate-500 for dark mode
    }
  },
  aov: {
    light: "#10b981", // emerald-500
    dark: "#34d399",  // emerald-400 for dark mode
    baseline: {
      light: "#94a3b8", // slate-400
      dark: "#64748b",  // slate-500 for dark mode
    }
  }
};
