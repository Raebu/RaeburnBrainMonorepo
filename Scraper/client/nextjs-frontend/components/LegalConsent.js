// client/nextjs-frontend/components/LegalConsent.js
import React from 'react';

export default function LegalConsent({ accepted, onChange }) {
  return (
    <div className="bg-muted border border-border rounded p-4 mt-4"> {/* Using Raeburn classes */}
      <div className="flex">
        <div className="flex-shrink-0">
          {/* Warning Icon - Using a simple exclamation mark in a circle as an example */}
          {/* You could also use an SVG icon library or import an SVG file */}
          <div className="w-5 h-5 rounded-full bg-yellow-100 text-yellow-800 flex items-center justify-center">
            <span className="text-xs font-bold">!</span>
          </div>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-gray-800"> {/* Adjusted text color for better contrast on muted background */}
            Legal Responsibility
          </h3>
          <div className="mt-2 text-sm text-gray-700">
            <p>
              By using Raeburn-Scraper, you agree that:
            </p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>You are responsible for complying with website Terms of Service</li>
              <li>You will respect robots.txt guidelines and rate limits</li>
              <li>You have legal rights to access the data you are scraping</li>
              <li>You understand data privacy regulations (GDPR, CCPA, etc.)</li>
              <li>You will use the service ethically and legally</li>
            </ul>
            <p className="mt-3 font-medium">
              Raeburn-Scraper is a proprietary project of The Raeburn Group. <br />
              &copy; {new Date().getFullYear()} The Raeburn Group. All rights reserved.
            </p>
          </div>
          <div className="mt-4">
            <div className="flex items-start">
              <div className="flex items-center h-5">
                <input
                  id="consent"
                  name="consent"
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => onChange(e.target.checked)}
                  className="h-4 w-4 text-primary border-border rounded focus:ring-primary" // Using Raeburn colors
                  required
                />
              </div>
              <div className="ml-3 text-sm">
                <label htmlFor="consent" className="font-medium text-gray-800">
                  I understand and accept these responsibilities
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
