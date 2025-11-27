// client/nextjs-frontend/components/Layout.js
import Header from './Header';
import Footer from './Footer';

export default function Layout({ children }) {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Header at the top */}
      <Header />
      
      {/* Main content area that grows to fill available space */}
      <main className="flex-grow container mx-auto px-4 py-8">
        {children}
      </main>
      
      {/* Footer at the bottom */}
      <Footer />
    </div>
  );
}
