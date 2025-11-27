// Import global styles first
import '../styles/globals.css';
import { AuthProvider } from '../lib/auth'; // Adjust path if lib is outside pages
import Header from '../components/Header'; // Adjust path if needed
import { useState, useEffect } from 'react';

// If you want to use the Inter font via @next/font (recommended for performance)
// Uncomment the lines below and the related parts in the component function
// import { Inter } from '@next/font/google';
// const inter = Inter({ subsets: ['latin'] });

function MyApp({ Component, pageProps }) {
  const [showHeader, setShowHeader] = useState(false);

  // Simple logic to hide header on auth pages
  // You can make this more sophisticated if needed
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname;
      setShowHeader(!['/login', '/signup'].includes(path));
    }
  }, []);

  // Wrap the entire app with AuthProvider for global auth state
  // Apply the Inter font className if using @next/font
  return (
    // If using @next/font, wrap like this:
    // <main className={inter.className}>
    <AuthProvider>
      {showHeader && <Header />}
      {/* Add padding top to content if header is shown */}
      <div className={showHeader ? "pt-16" : ""}> 
        <Component {...pageProps} />
      </div>
    </AuthProvider>
    // </main>
  );
}

export default MyApp;
