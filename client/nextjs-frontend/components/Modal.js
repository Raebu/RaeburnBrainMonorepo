import { useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';

export default function Modal({ isOpen, onClose, title, children, actions }) {
  const modalRef = useRef(null);

  // Close modal on Escape key press
  useEffect(() => {
    const handleEsc = (event) => {
      if (event.keyCode === 27) { // Escape key
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEsc);
      // Prevent background scrolling when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  // Close modal if clicked outside content
  const handleBackdropClick = (e) => {
    if (modalRef.current === e.target) {
      onClose();
    }
  };

  // Don't render if not open
  if (!isOpen) return null;

  return ReactDOM.createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      onClick={handleBackdropClick}
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      <div className="card w-full max-w-md mx-auto bg-light"> {/* Use card and bg-light classes */}
        {/* Modal Header */}
        {title && (
          <div className="border-b border-border p-4 flex justify-between items-center">
            <h3 id="modal-title" className="text-lg font-medium">
              {title}
            </h3>
            <button
              onClick={onClose}
              className="text-muted hover:text-primary focus:outline-none focus:text-primary"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-4">
          {children}
        </div>

        {/* Modal Footer / Actions */}
        {actions && (
          <div className="border-t border-border p-4 flex justify-end space-x-3">
            {actions}
          </div>
        )}
      </div>
    </div>,
    document.body // Render modal directly to body
  );
}
