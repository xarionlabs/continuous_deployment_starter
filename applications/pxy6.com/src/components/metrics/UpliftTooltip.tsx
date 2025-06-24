
import React from "react";
import { ChartTooltipContent } from "@/components/ui/chart";
import { TooltipProps } from "recharts";

export const UpliftTooltip = ({ active, payload, label }: TooltipProps<number, string>) => {
  if (active && payload && payload.length) {
    const baseline = Number(payload[0]?.value || 0).toFixed(1);
    const uplift = payload.length > 1 ? Number(payload[1]?.value || 0).toFixed(1) : "N/A";
    const difference = (Number(uplift) - Number(baseline)).toFixed(1);
    const percentageUplift = Math.round((Number(difference) / Number(baseline)) * 100);

    return (
      <div className="rounded-lg border bg-background p-2 shadow-sm">
        <div className="grid grid-cols-2 gap-2">
          <div className="flex flex-col">
            <span className="text-[0.70rem] uppercase text-muted-foreground">
              {label}
            </span>
            <span className="font-bold text-muted-foreground">
              Baseline: {baseline}
            </span>
            <span className="font-bold text-emerald-500">
              Uplift: {uplift}
            </span>
            <span className="text-sm text-emerald-500">
              +{difference} ({percentageUplift}%)
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};
