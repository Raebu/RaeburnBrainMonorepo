// client/nextjs-frontend/components/UsageChart.js
import React from 'react';

/**
 * A simple bar chart component to display usage quota.
 * 
 * @param {{ quota: { usedToday: number, dailyLimit: number } }} props 
 * @returns {JSX.Element}
 */
export default function UsageChart({ quota }) {
  if (!quota) {
    return null; // Or render a loading state if preferred
  }

  const { usedToday, dailyLimit } = quota;
  const percentage = Math.min((usedToday / dailyLimit) * 100, 100); // Cap at 100%
  const isNearLimit = percentage > 80;

  // Determine bar color based on usage
  let barColorClass = 'bg-primary'; // Default black
  if (percentage > 90) {
    barColorClass = 'bg-dark-bg'; // Dark gray for high usage
  } else if (percentage > 70) {
    barColorClass = 'bg-accent'; // Accent gray for medium usage
  }

  return (
    <div className="card p-4">
      <h3 className="text-lg font-medium mb-4">Daily Usage</h3>
      
      <div className="mb-2 flex justify-between text-sm">
        <span>Jobs Used</span>
        <span>
          <strong>{usedToday}</strong> / {dailyLimit}
        </span>
      </div>

      {/* Chart Container */}
      <div 
        className="w-full bg-muted rounded-full h-4 overflow-hidden border border-border" 
        role="progressbar" 
        aria-valuenow={usedToday} 
        aria-valuemin="0" 
        aria-valuemax={dailyLimit}
        aria-label="Daily scraping quota usage"
      >
        {/* Usage Bar */}
        <div
          className={`h-full ${barColorClass} transition-all duration-500 ease-in-out`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>

      {/* Status Message */}
      {isNearLimit && (
        <p className="mt-3 text-xs text-muted">
          {/* Using text-muted for a subtle warning, you could also add a dedicated warning color if desired */}
          Approaching daily limit. Consider upgrading for more capacity.
        </p>
      )}
      
      {usedToday >= dailyLimit && (
         <p className="mt-3 text-xs text-muted">
            Daily limit reached. Please wait until tomorrow or upgrade your plan.
         </p>
      )}
    </div>
  );
}
