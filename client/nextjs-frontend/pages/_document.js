// client/nextjs-frontend/pages/_document.js
import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Preconnect to Google Fonts for faster loading */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Load the Inter font stylesheet */}
        {/* Weights 400 (Regular), 500 (Medium), and 700 (Bold) are commonly used */}
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
        {/* 
          Optional: Add a favicon if you have one for Raeburn-Scraper
          <link rel="icon" href="/favicon.ico" /> 
        */}
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
