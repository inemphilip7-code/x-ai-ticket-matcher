import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'X AI Ticket-Matcher Bot',
  description: 'AI-Powered Secondary Ticket Search, Anti-Fraud Verification, and Direct Matching Bot for X',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090b10] text-slate-100 min-h-screen antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
