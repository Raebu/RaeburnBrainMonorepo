import { useState } from 'react';
import { useAuth } from '../../lib/auth';
import ErrorMessage from './ErrorMessage';
import LoadingSpinner from './LoadingSpinner';

export default function SessionManager({ sessions = [], onAddSession, onDeleteSession, loading: propLoading }) {
  const { user } = useAuth();
  const [isAdding, setIsAdding] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [error, setError] = useState('');
  const [localLoading, setLocalLoading] = useState(false);

  const handleAddClick = () => {
    setIsAdding(true);
    setError('');
  };

  const handleCancelAdd = () => {
    setIsAdding(false);
    setNewSessionName('');
    setError('');
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    if (!newSessionName.trim()) {
      setError('Session name is required.');
      return;
    }

    setLocalLoading(true);
    setError('');

    try {
      // In a real implementation, this would trigger a process to capture
      // cookies from the user's current browser session.
      // For now, we simulate this with a placeholder.
      const placeholderSessionData = {
        name: newSessionName,
        // In reality, cookies and userAgent would be captured securely here
        cookies: '[]', // Placeholder - should be actual encrypted cookie data
        userAgent: navigator.userAgent,
      };

      await onAddSession(placeholderSessionData);
      setNewSessionName('');
      setIsAdding(false);
    } catch (err) {
      console.error("Session add error:", err);
      setError(err.message || 'Failed to add session. Please try again.');
    } finally {
      setLocalLoading(false);
    }
  };

  const handleDeleteClick = async (sessionId) => {
    if (window.confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      setLocalLoading(true);
      try {
        await onDeleteSession(sessionId);
      } catch (err) {
        console.error("Session delete error:", err);
        setError(err.message || 'Failed to delete session. Please try again.');
      } finally {
        setLocalLoading(false);
      }
    }
  };

  const isLoading = propLoading || localLoading;

  return (
    <div className="card p-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">Browser Sessions</h3>
        {!isAdding && (
          <button
            onClick={handleAddClick}
            className="btn btn-primary text-sm"
            disabled={isLoading}
          >
            Add New Session
          </button>
        )}
      </div>

      {error && <ErrorMessage message={error} />}

      {isLoading && <LoadingSpinner />}

      {isAdding && (
        <form onSubmit={handleAddSubmit} className="mb-6 p-4 bg-muted rounded">
          <h4 className="text-md font-medium mb-3">Add New Session</h4>
          <div className="mb-3">
            <label htmlFor="sessionName" className="block text-sm font-medium mb-1">
              Session Name
            </label>
            <input
              type="text"
              id="sessionName"
              value={newSessionName}
              onChange={(e) => setNewSessionName(e.target.value)}
              required
              className="w-full"
              placeholder="e.g., LinkedIn Work Account"
              disabled={isLoading}
            />
          </div>
          <div className="flex space-x-2">
            <button
              type="submit"
              className="btn btn-primary text-sm"
              disabled={isLoading}
            >
              {isLoading ? 'Adding...' : 'Add Session'}
            </button>
            <button
              type="button"
              onClick={handleCancelAdd}
              className="btn btn-secondary text-sm"
              disabled={isLoading}
            >
              Cancel
            </button>
          </div>
          <p className="mt-2 text-xs text-muted">
            <strong>Note:</strong> Adding a session typically involves securely uploading your browser cookies for the target website. This ensures Raeburn-Scraper can access the site on your behalf.
          </p>
        </form>
      )}

      {sessions && sessions.length > 0 ? (
        <ul className="list-none">
          {sessions.map((session) => (
            <li key={session.id} className="flex justify-between items-center py-3 border-b border-border">
              <div>
                <span className="font-medium">{session.name}</span>
                <span className="text-xs text-muted ml-2">
                  (Added: {new Date(session.createdAt).toLocaleDateString()})
                </span>
              </div>
              <button
                onClick={() => handleDeleteClick(session.id)}
                className="btn btn-secondary text-sm"
                disabled={isLoading}
                aria-label={`Delete session ${session.name}`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      ) : (
        !isAdding && !isLoading && (
          <p className="text-muted text-center py-4">
            No sessions found. Add a session to start scraping with your authenticated accounts.
          </p>
        )
      )}
    </div>
  );
}
