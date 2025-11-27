// client/nextjs-frontend/components/JobStatus.js
import React from 'react';

/**
 * Component to display the status of a scraping job.
 * 
 * @param {Object} props - The component props.
 * @param {string} props.status - The current status of the job (e.g., 'queued', 'processing', 'completed', 'failed', 'waiting_for_captcha').
 * @param {string} [props.className] - Additional CSS classes to apply.
 * @returns {JSX.Element} The rendered JobStatus component.
 */
export default function JobStatus({ status, className = '' }) {
  // Map status to display text and CSS class
  const statusConfig = {
    queued: { text: 'Queued', className: 'status-queued' },
    processing: { text: 'Processing', className: 'status-processing' },
    completed: { text: 'Completed', className: 'status-completed' },
    failed: { text: 'Failed', className: 'status-failed' },
    waiting_for_captcha: { text: 'CAPTCHA Required', className: 'status-waiting_for_captcha' },
    // Add more statuses as needed
    default: { text: status, className: 'status-default' } // Fallback
  };

  const config = statusConfig[status] || statusConfig.default;

  return (
    <span className={`status-badge ${config.className} ${className}`}>
      {config.text}
    </span>
  );
}
