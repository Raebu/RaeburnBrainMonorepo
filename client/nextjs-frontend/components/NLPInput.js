// client/nextjs-frontend/components/NLPInput.js
import { useState } from 'react';

/**
 * A component for submitting natural language scraping requests.
 *
 * @param {Object} props
 * @param {Function} props.onSubmit - Function to call when the form is submitted. Receives the prompt string.
 * @param {boolean} [props.loading=false] - Indicates if a request is currently processing.
 * @param {string} [props.error=null] - An error message to display.
 * @param {string} [props.domain=''] - Optional domain hint to guide the LLM.
 */
export default function NLPInput({ onSubmit, loading = false, error = null, domain = '' }) {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim() && onSubmit && !loading) {
      onSubmit(prompt.trim());
    }
  };

  return (
    <div className="card p-4"> {/* Use .card for consistent styling */}
      <h3 className="mb-4">Natural Language Scraping</h3>
      <p className="text-muted mb-4"> {/* Use .text-muted for secondary text */}
        Describe what you want to scrape in plain English.
        {/* Example prompt for guidance */}
        <br />
        <em>E.g., "Find product managers in London on LinkedIn"</em>
      </p>

      {error && (
        <div className="error-message mb-4 p-3 rounded"> {/* Reuse error styling */}
          <p className="m-0">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="nlpPrompt" className="block mb-2 font-medium">
            Your Request
          </label>
          <textarea
            id="nlpPrompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Scrape job titles and companies for all product managers in London."
            rows="3"
            required
            disabled={loading}
            className="w-full p-3 border border-border rounded bg-secondary text-primary" // Use design system variables
          />
        </div>

        {domain && (
          <div className="mb-4 text-sm text-muted">
            <p>Targeting domain: <strong>{domain}</strong></p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className={`btn btn-primary w-full ${loading ? 'opacity-75 cursor-not-allowed' : ''}`} // Use .btn-primary
        >
          {loading ? (
            <>
              <span className="loading-spinner mr-2"></span> {/* Reuse spinner */}
              Processing...
            </>
          ) : (
            'Create Scraping Job'
          )}
        </button>
      </form>
    </div>
  );
}
