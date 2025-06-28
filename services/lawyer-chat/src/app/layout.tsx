import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import DarkModeWrapper from "@/components/DarkModeWrapper";
import ClientErrorHandler from "./ClientErrorHandler";
import "@/lib/fetch-polyfill";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lawyer Chat - AI Legal Assistant",
  description: "AI-powered legal document processing and chat interface",
  icons: {
    icon: '/chat/logo.png',
    shortcut: '/chat/logo.png',
    apple: '/chat/logo.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <Providers>
          <DarkModeWrapper>
            <ClientErrorHandler />
            {children}
          </DarkModeWrapper>
        </Providers>
      </body>
    </html>
  );
}
