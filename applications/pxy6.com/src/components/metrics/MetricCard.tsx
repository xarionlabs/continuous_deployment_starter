
import React from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TrendDisplay } from "./TrendDisplay";
import { MetricCardProps } from "./types";

export const MetricCard = ({ title, value, trend, period, baseline, uplift, children }: MetricCardProps) => {
  const difference = uplift && baseline ? uplift - baseline : 0;
  const percentageUplift = baseline ? Math.round((difference / baseline) * 100) : 0;

  return (
    <Card className="w-full overflow-hidden">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="text-2xl font-bold">{value}</div>
            <TrendDisplay trend={trend} period={period} />
          </div>
          {baseline !== undefined && uplift !== undefined && (
            <div className="flex flex-col gap-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Baseline:</span>
                <span className="font-medium">{baseline}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-emerald-500">Uplift:</span>
                <span className="font-medium text-emerald-500">{uplift}</span>
              </div>
              <div className="flex items-center justify-between border-t pt-1">
                <span className="text-emerald-500">Improvement:</span>
                <span className="font-medium text-emerald-500">+{difference.toFixed(1)} ({percentageUplift}%)</span>
              </div>
            </div>
          )}
          <div className="h-[120px] w-full">
            {children}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
