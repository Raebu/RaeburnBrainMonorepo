// client/nextjs-frontend/pages/dashboard.js
import { useState, useEffect } from 'react';
import { useAuth } from '../lib/auth';
import { useRouter } from 'next/router';
import Header from '../components/Header';
import JobForm from '../components/JobForm';
import JobList from '../components/JobList';
import QuotaDisplay from '../components/QuotaDisplay';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [error, setError] = useState('');
  const [jobsError, setJobsError] = useState('');

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    fetchJobs();
  }, [user]);

  const fetchJobs = async () => {
    setJobsLoading(true);
    setJobsError('');
    try {
      const res = await fetch('/api/scraping/jobs');
      if (!res.ok) throw new Error('Failed to fetch jobs');
      const data = await res.json();
      setJobs(data);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      setJobsError('Failed to load jobs. Please try again.');
    } finally {
      setJobsLoading(false);
    }
  };

  const handleCreateJob = async (jobData) => {
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/scraping/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: jobData.url,
          selectors: {
            container: jobData.container,
            fields: {
              name: jobData.nameSelector,
              title: jobData.titleSelector,
              company: jobData.companySelector
            }
          },
          config: {
            sessionId: jobData.sessionId
          }
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to create job');
      }

      // Refresh job list after creation
      await fetchJobs();
    } catch (error) {
      console.error('Failed to create job:', error);
      setError(error.message || 'Failed to create job. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewResults = async (jobId) => {
    try {
      // This will redirect to the results endpoint which handles the download
      window.open(`/api/scraping/results/${jobId}`, '_blank');
    } catch (error) {
      console.error('Failed to view results:', error);
      // Optionally show an error message to the user
    }
  };

  if (!user) return <LoadingSpinner />; // Or redirect handled by useEffect

  return (
    <div className="min-h-screen bg-light">
      <Header />

      <main className="container mx-auto py-6">
        <div className="dashboard-header mb-6">
          <h1 className="dashboard-title">Raeburn-Scraper Dashboard</h1>
          <p className="text-muted">Welcome back, {user.name}</p>
        </div>

        <div className="dashboard-content">
          {/* Quota Display */}
          <div className="dashboard-section mb-6">
            <div className="card p-4">
              <h2 className="dashboard-section-title">Your Usage</h2>
              <QuotaDisplay quota={user.quota} />
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="dashboard-section mb-6">
              <ErrorMessage message={error} />
            </div>
          )}

          <div className="grid col-1 lg:col-2 gap-6">
            {/* Job Creation Form */}
            <div className="dashboard-section">
              <div className="card p-6">
                <h2 className="dashboard-section-title">Create New Scraping Job</h2>
                <JobForm onSubmit={handleCreateJob} loading={loading} />
              </div>
            </div>

            {/* Job List */}
            <div className="dashboard-section">
              <div className="card p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="dashboard-section-title mb-0">Recent Jobs</h2>
                  <button
                    onClick={fetchJobs}
                    disabled={jobsLoading}
                    className="btn btn-secondary text-sm"
                  >
                    {jobsLoading ? 'Refreshing...' : 'Refresh'}
                  </button>
                </div>

                {jobsError ? (
                  <ErrorMessage message={jobsError} onRetry={fetchJobs} />
                ) : jobsLoading ? (
                  <LoadingSpinner />
                ) : jobs.length > 0 ? (
                  <JobList jobs={jobs} onViewResults={handleViewResults} />
                ) : (
                  <p className="text-muted">No jobs found. Create your first job!</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
