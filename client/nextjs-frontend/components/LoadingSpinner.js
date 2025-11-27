import React from 'react';

/**
 * A simple loading spinner using CSS, styled with The Raeburn Group's design system.
 * It uses the primary color (#000000) for the spinning element.
 */
export default function LoadingSpinner({ size = 'md', message = null }) {
  // Define size variants using the design system's scale if needed
  // For now, we'll use simple CSS classes
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div
        className={`${sizeClasses[size] || sizeClasses.md} border-4 border-muted border-t-primary rounded-full animate-spin`}
        role="status"
        aria-label="Loading"
      ></div>
      {message && <p className="mt-2 text-muted text-sm">{message}</p>}
    </div>
  );
}
