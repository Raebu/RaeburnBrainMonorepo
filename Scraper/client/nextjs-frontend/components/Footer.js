import React from 'react';
import Link from 'next/link';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-dark bg-light py-8 text-center text-sm text-muted">
      <div className="container">
        <p>
          Raeburn-Scraper is a proprietary project of The Raeburn Group.
          <br />
          © {currentYear} The Raeburn Group. All rights reserved.
        </p>
        <nav className="flex justify-center space-x-4 mt-4">
          <Link href="/privacy-policy" className="text-muted hover:text-primary">
            Privacy Policy
          </Link>
          <Link href="/terms-of-service" className="text-muted hover:text-primary">
            Terms of Service
          </Link>
        </nav>
      </div>
    </footer>
  );
}
