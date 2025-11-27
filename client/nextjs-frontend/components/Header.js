// client/nextjs-frontend/components/Header.js
import Link from 'next/link';
import { useAuth } from '../../lib/auth';

export default function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="header"> {/* Apply Raeburn 'header' class */}
      <div className="container"> {/* Apply Raeburn 'container' class */}
        <div className="flex justify-between items-center h-16"> {/* Apply Raeburn 'flex' class */}
          <div className="flex items-center">
            {/* Raeburn-styled logo and name */}
            <Link href="/dashboard" className="logo-link flex items-center"> {/* Combine utility classes */}
              <div className="logo" aria-label="Raeburn Scraper Logo"></div> {/* Apply Raeburn 'logo' class */}
              <span className="logo-text ml-4 text-xl font-bold"> {/* Use utility classes for spacing and style */}
                Raeburn-Scraper
              </span>
            </Link>
            {/* Navigation */}
            <nav className="ml-6 flex"> {/* Apply Raeburn 'flex' class */}
              <Link href="/dashboard" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-muted">
                Dashboard
              </Link>
              <Link href="/sessions" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-muted">
                Sessions
              </Link>
              <Link href="/history" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-muted">
                History
              </Link>
            </nav>
          </div>
          {/* User Authentication Section */}
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <span className="text-sm text-gray-700 hidden md:inline">
                  {user.name}
                </span>
                {/* Use Raeburn-styled button */}
                <button
                  onClick={logout}
                  className="btn btn-secondary text-sm" // Apply Raeburn button classes
                >
                  Logout
                </button>
              </>
            ) : (
              // Use Raeburn-styled button for login link
              <Link href="/login" className="btn btn-primary text-sm"> // Apply Raeburn button classes
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
