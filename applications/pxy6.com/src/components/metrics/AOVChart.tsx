
import React from "react";
import { LineChartWithUplift } from "./LineChartWithUplift";
import { Tooltip } from "recharts";
import { UpliftTooltip } from "./UpliftTooltip";
import { MetricDataPoint } from "./types";

type AOVChartProps = {
  data: MetricDataPoint[];
  theme: "light" | "dark";
  colors: {
    light: string;
    dark: string;
    baseline: {
      light: string;
      dark: string;
    }
  };
};

export const AOVChart = ({ data, theme, colors }: AOVChartProps) => {
  // Get the color based on current theme
  const chartColor = colors[theme];
  const baselineColor = colors.baseline[theme];

  return (
    <>
      <LineChartWithUplift
        data={data}
        baselineKey="baseline"
        upliftKey="uplift"
        chartId="aov"
        colorConfig={chartColor}
        baselineColor={baselineColor}
      />
      {/* Add tooltip directly in parent component */}
      <Tooltip content={<UpliftTooltip />} />
    </>
  );
};
