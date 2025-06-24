
import React from "react";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

type TrendDisplayProps = {
  trend: number;
  period: string;
};

export const TrendDisplay = ({ trend, period }: TrendDisplayProps) => {
  if (trend > 0) {
    return (
      <div className="flex items-center space-x-1 text-sm">
        <div className="flex items-center text-emerald-500">
          <ArrowUp className="mr-1 h-4 w-4" />
          {Math.abs(Math.round(trend))}%
        </div>
        <span className="text-muted-foreground">vs {period}</span>
      </div>
    );
  } else if (trend < 0) {
    return (
      <div className="flex items-center space-x-1 text-sm">
        <div className="flex items-center text-red-500">
          <ArrowDown className="mr-1 h-4 w-4" />
          {Math.abs(Math.round(trend))}%
        </div>
        <span className="text-muted-foreground">vs {period}</span>
      </div>
    );
  } else {
    return (
      <div className="flex items-center space-x-1 text-sm">
        <div className="flex items-center text-gray-500">
          <Minus className="mr-1 h-4 w-4" />
          0%
        </div>
        <span className="text-muted-foreground">vs {period}</span>
      </div>
    );
  }
};
