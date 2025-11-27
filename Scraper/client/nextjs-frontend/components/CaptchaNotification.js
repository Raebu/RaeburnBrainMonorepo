// client/nextjs-frontend/components/CaptchaNotification.js
import React, { useState } from 'react';

/**
 * Notification component for CAPTCHA events.
 * 
 * @param {Object} props - Component properties.
 * @param {string} props.jobId - The ID of the scraping job requiring CAPTCHA solving.
 * @param {Object} props.captchaInfo - Details about the detected CAPTCHA (type, element, etc.).
 * @param {Function} props.onPauseJob - Function to call when the user wants to pause the job.
 * @param {Function} props.onGetHelp - Function to call when the user requests help.
 * @param {Function} props.onClose - Function to call to dismiss the notification.
 */
export default function CaptchaNotification({ jobId, captchaInfo, onPauseJob, onGetHelp, onClose }) {
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    // Allow animation to play before calling parent onClose
    setTimeout(() => {
      if (onClose) onClose();
    }, 300); // Match CSS transition duration
  };

  const handlePause = () => {
    handleClose();
    if (onPauseJob) onPauseJob(jobId);
  };

  const handleHelp = () => {
    handleClose();
    if (onGetHelp) onGetHelp(jobId);
  };

  // Determine CAPTCHA type description
  let captchaType = 'Security Check';
  if (captchaInfo?.type) {
    if (captchaInfo.type.includes('recaptcha')) {
      captchaType = 'Google reCAPTCHA';
    } else if (captchaInfo.type.includes('hcaptcha')) {
      captchaType = 'hCaptcha';
    } else if (captchaInfo.type.includes('cloudflare')) {
      captchaType = 'Cloudflare Challenge';
    } else {
      captchaType = `${captchaInfo.type.charAt(0).toUpperCase() + captchaInfo.type.slice(1)} Challenge`;
    }
  }

  return (
    <div className={`fixed inset-0 z-50 flex items-end justify-center px-4 py-6 pointer-events-none sm:items-start sm:justify-end ${isClosing ? 'opacity-0' : 'opacity-100'} transition-opacity duration-300`}>
      <div className={`pointer-events-auto w-full max-w-sm rounded-lg shadow-lg bg-light border border-border overflow-hidden transform transition-transform duration-300 ${isClosing ? 'translate-y-4' : 'translate-y-0'}`}>
        <div className="p-4">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              {/* Warning Icon */}
              <svg className="h-6 w-6 text-yellow-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="ml-3 w-0 flex-1 pt-0.5">
              <p className="text-sm font-medium text-primary">
                CAPTCHA Detected
              </p>
              <p className="mt-1 text-sm text-muted">
                {captchaType} required for job <span className="font-mono">{jobId.substring(0, 8)}...</span>
              </p>
              <div className="mt-3 flex space-x-3">
                <button
                  type="button"
                  onClick={handlePause}
                  className="btn btn-secondary text-sm px-3 py-1.5"
                >
                  Pause Job
                </button>
                <button
                  type="button"
                  onClick={handleHelp}
                  className="btn btn-primary text-sm px-3 py-1.5"
                >
                  Get Help
                </button>
              </div>
            </div>
            <div className="ml-4 flex-shrink-0 flex">
              <button
                type="button"
                onClick={handleClose}
                className="bg-light rounded-md inline-flex text-muted hover:text-primary focus:outline-none"
              >
                <span className="sr-only">Close</span>
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
