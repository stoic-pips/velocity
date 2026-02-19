import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import InstallPWA from "@/components/InstallPWA";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Dunam Velocity",
  description: "Stoic Trading Bot Dashboard",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Velocity",
  },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.variable}>
        {children}
        <InstallPWA />
      </body>
    </html>
  );
}
