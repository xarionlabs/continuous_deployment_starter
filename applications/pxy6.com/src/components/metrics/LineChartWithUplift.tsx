
import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Area,
} from "recharts";
import { ChartContainer } from "@/components/ui/chart";
import { ChartProps, MetricDataPoint } from "./types";

export const LineChartWithUplift = ({ 
  data,
  baselineKey,
  upliftKey = "uplift",
  chartId,
  colorConfig,
  baselineColor
}: ChartProps) => {
  // Use a string color that works for both themes
  const chartColorStr = typeof colorConfig === "string" ? 
    colorConfig : 
    "#10b981"; // Default to emerald-500 if object passed
  
  const baselineColorStr = baselineColor || "#94a3b8"; // Default to slate-400

  // Create a theme configuration suitable for ChartContainer
  const chartConfig = {
    [chartId]: {
      theme: typeof colorConfig === "object" ? 
        { light: colorConfig.light, dark: colorConfig.dark } : 
        { light: chartColorStr, dark: chartColorStr }
    }
  };

  // Unique gradient ID to prevent conflicts when multiple charts are used
  const gradientId = `${chartId}UpliftGradient`;

  return (
    <div className="w-full h-full">
      <ChartContainer
        config={chartConfig}
        className="w-full h-full"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis 
              dataKey="month" 
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12 }}
              dy={10}
            />
            <YAxis hide />
            
            {/* We'll handle tooltips outside this component */}
            
            {/* Baseline line */}
            <Line
              type="monotone"
              dataKey={baselineKey}
              name="baseline"
              stroke={baselineColorStr}
              strokeWidth={2}
              dot={false}
              strokeDasharray="5 5"
            />
            
            {/* Uplift line */}
            <Line
              type="monotone"
              dataKey={upliftKey}
              name="uplift"
              stroke={chartColorStr}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6, fill: chartColorStr }}
            />
            
            {/* Area showing the uplift */}
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartColorStr} stopOpacity={0.1}/>
                <stop offset="95%" stopColor={chartColorStr} stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey={upliftKey}
              stroke="false"
              fill={`url(#${gradientId})`}
              fillOpacity={0.3}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>
    </div>
  );
};
