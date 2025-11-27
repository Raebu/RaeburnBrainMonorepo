// client/nextjs-frontend/components/JobList.js
import React from 'react';
import Link from 'next/link'; // If you need internal navigation for results

export default function JobList({ jobs = [], onViewResults, className = '' }) {
  // Helper function to determine status badge style
  const getStatusClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'status-completed'; // Defined in globals.css
      case 'failed':
        return 'status-failed';
      case 'processing':
        return 'status-processing';
      case 'queued':
        return 'status-queued';
      case 'waiting_for_captcha':
        return 'status-waiting_for_captcha';
      default:
        return 'status-queued'; // Default fallback
    }
  };

  if (jobs.length === 0) {
    return (
      <div className={`card p-8 text-center ${className}`}>
        <p className="text-muted">No scraping jobs found. Create one to get started!</p>
      </div>
    );
  }

  return (
    <div className={`card ${className}`}>
      <ul className="list-none divide-y divide-border"> {/* divide-border from globals.css */}
        {jobs.map((job) => (
          <li key={job.id} className="p-4 hover:bg-muted transition-colors duration-200">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
              <div className="min-w-0"> {/* Helps with text truncation */}
                <h3 className="font-medium text-primary truncate" title={job.url}>
                  {job.url}
                </h3>
                <div className="flex items-center text-sm text-muted mt-1">
                  <svg className="flex-shrink-0 mr-1.5 h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                  </svg>
                  <span>
                    Created: {new Date(job.createdAt).toLocaleDateString()} at {new Date(job.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
              <div className="flex-shrink-0 flex flex-col sm:flex-row sm:items-center gap-2">
                <span className={`status-badge ${getStatusClass(job.status)}`}>
                  {job.status.replace(/_/g, ' ')} {/* Replace underscores with spaces */}
                </span>
                {job.status === 'completed' && job.resultUrl && onViewResults && (
                  <button
                    onClick={() => onViewResults(job.id)}
                    className="btn btn-secondary text-sm py-1 px-3" // Smaller button
                  >
                    Download Results
                  </button>
                )}
                {job.status === 'waiting_for_captcha' && (
                  <span className="text-sm font-medium text-accent"> {/* text-accent from globals.css */}
                    CAPTCHA Required
                  </span>
                )}
                {/* Optional: Add a link to view job details if you have a dedicated job page */}
                {/* <Link href={`/jobs/${job.id}`} className="text-sm text-primary hover:underline">
                  View Details
                </Link> */}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
