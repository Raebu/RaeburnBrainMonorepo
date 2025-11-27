import React from 'react';

export default function QuotaDisplay({ quota }) {
  if (!quota) return null;

  const percentage = (quota.usedToday / quota.dailyLimit) * 100;
  const isNearLimit = percentage > 80;

  // Determine bar color based on usage
  let barColorClass = 'bg-muted'; // Default light gray
  if (percentage > 90) {
    barColorClass = 'bg-dark'; // Use dark color for high usage (black)
  } else if (percentage > 70) {
    barColorClass = 'bg-accent'; // Use accent color for medium usage (gray)
  }
  // For <= 70%, it remains the default light gray

  return (
    <div className={`card p-4 ${isNearLimit ? 'border border-warning' : ''}`}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium">Daily Usage</span>
        <span className="text-sm">
          {quota.usedToday} / {quota.dailyLimit}
        </span>
      </div>
      <div className="w-full bg-muted rounded-full h-2 overflow-hidden"> {/* Background track */}
        <div
          className={`h-2 rounded-full ${barColorClass}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
          role="progressbar"
          aria-valuenow={quota.usedToday}
          aria-valuemin="0"
          aria-valuemax={quota.dailyLimit}
        ></div>
      </div>
      {isNearLimit && (
        <p className="mt-2 text-xs text-muted">
          You're approaching your daily limit. Consider upgrading for more capacity.
        </p>
      )}
    </div>
  );
}
