// client/nextjs-frontend/components/JobForm.js
import { useState } from 'react';
import Link from 'next/link'; // If you need links within the form

export default function JobForm({ onSubmit, loading, sessions = [] }) { // Accept sessions as prop
  const [formData, setFormData] = useState({
    url: '',
    sessionId: '', // Added sessionId
    container: '.search-result', // Default LinkedIn selector example
    nameSelector: '.entity-result__title a span',
    titleSelector: '.entity-result__primary-subtitle',
    companySelector: '.entity-result__secondary-subtitle',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    // Basic validation could be added here if needed
    onSubmit(formData);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="card p-8"> {/* Use card class for styling */}
      <div className="flex items-center mb-6">
        <div className="raeburn-logo" aria-label="Raeburn Scraper Logo"></div>
        <h2 className="ml-4 text-2xl font-bold">Raeburn-Scraper</h2> {/* Use h2 size and project name */}
      </div>
      <p className="mb-6 text-muted"> {/* Use text-muted for descriptive text */}
        Configure your scraping job. Select a saved browser session and specify the elements to extract.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="form-group">
          <label htmlFor="url" className="block text-sm font-medium mb-1">
            Target URL *
          </label>
          <input
            type="url"
            name="url"
            id="url"
            required
            value={formData.url}
            onChange={handleChange}
            placeholder="https://linkedin.com/search/results/people/..."
            className="w-full" // Input styles are defined in globals.css
          />
        </div>

        <div className="form-group">
          <label htmlFor="sessionId" className="block text-sm font-medium mb-1">
            Browser Session *
          </label>
          <select
            name="sessionId"
            id="sessionId"
            required
            value={formData.sessionId}
            onChange={handleChange}
            className="w-full"
          >
            <option value="">Select a session</option>
            {sessions.map((session) => (
              <option key={session.id} value={session.id}>
                {session.name} {/* Assumes session object has 'name' and 'id' */}
              </option>
            ))}
            {/* Example static options if sessions prop isn't used initially */}
            {/* <option value="session-123">My LinkedIn Session</option>
            <option value="session-456">My Job Board Session</option> */}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="container" className="block text-sm font-medium mb-1">
            Container Selector *
          </label>
          <input
            type="text"
            name="container"
            id="container"
            required
            value={formData.container}
            onChange={handleChange}
            placeholder=".search-result"
            className="w-full"
          />
          <p className="mt-1 text-xs text-muted">
            CSS selector for the main result item wrapper.
          </p>
        </div>

        {/* Fields Section */}
        <fieldset className="border border-border rounded p-4"> {/* Use border utilities */}
          <legend className="text-sm font-medium px-1">Fields to Extract</legend>
          <div className="space-y-4 mt-3">
            <div className="form-group">
              <label htmlFor="nameSelector" className="block text-sm font-medium mb-1">
                Name Selector *
              </label>
              <input
                type="text"
                name="nameSelector"
                id="nameSelector"
                required
                value={formData.nameSelector}
                onChange={handleChange}
                placeholder=".name"
                className="w-full"
              />
            </div>

            <div className="form-group">
              <label htmlFor="titleSelector" className="block text-sm font-medium mb-1">
                Title Selector *
              </label>
              <input
                type="text"
                name="titleSelector"
                id="titleSelector"
                required
                value={formData.titleSelector}
                onChange={handleChange}
                placeholder=".title"
                className="w-full"
              />
            </div>

            <div className="form-group">
              <label htmlFor="companySelector" className="block text-sm font-medium mb-1">
                Company Selector *
              </label>
              <input
                type="text"
                name="companySelector"
                id="companySelector"
                required
                value={formData.companySelector}
                onChange={handleChange}
                placeholder=".company"
                className="w-full"
              />
            </div>
          </div>
        </fieldset>

        <div className="flex items-center justify-between">
          <p className="text-xs text-muted">
            * Required fields
          </p>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary" // Use primary button class
          >
            {loading ? (
              <>
                <span className="loading-spinner mr-2"></span> {/* Assuming you have this class */}
                Creating Job...
              </>
            ) : (
              'Start Scraping'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
