import React from 'react';

export default function SuccessMessage({ message, onDismiss }) {
  return (
    <div className="bg-light border border-border rounded-md p-4 my-4"> {/* Use Raeburn classes */}
      <div className="flex">
        <div className="flex-shrink-0">
          {/* Green checkmark icon */}
          <svg className="h-5 w-5 text-green-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1 md:flex md:justify-between">
          <p className="text-sm text-green-800"> {/* Use a darker green for text if desired, or stick to Raeburn text color */}
            {message}
          </p>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="btn btn-secondary text-sm mt-2 md:mt-0 md:ml-4 py-1 px-3" // Use Raeburn button style
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
