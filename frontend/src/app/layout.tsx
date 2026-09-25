import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
import { AuthProvider } from "@/lib/AuthProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Satmaps - Geospatial Verification & Watershed Context Platform",
  description: "PS 26015 - Places geo-coded field photographs in their actual watershed context — spatially, hydrologically, and temporally — to support evidence-based interpretation.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-[#0D0A18] text-[#F3F0FA]">
        <AuthProvider>
          <nav className="h-14 flex items-center justify-between gap-4 px-4 sm:px-6 border-b border-[#A997DF]/20 bg-[#161226]/95 text-[#F3F0FA] backdrop-blur-xl z-50 shrink-0">
            <div className="flex items-center gap-6">
              <Link href="/" className="font-bold text-base text-[#F3F0FA] flex items-center gap-2 hover:opacity-90 transition-opacity">
                <span className="text-xl">📡</span>
                <span className="lavender-gradient-text font-extrabold text-xl tracking-tight">Satmaps</span>
                <span className="text-[10px] font-bold bg-[#7058B6]/30 text-[#DCCFEC] px-2 py-0.5 rounded-full border border-[#A997DF]/30">PS 26015</span>
              </Link>
              <div className="hidden md:flex items-center gap-1 text-sm font-medium">
                <Link href="/assets" className="px-3 py-1.5 rounded-lg text-[#C3B8DF] hover:text-white hover:bg-[#221C3A] transition-colors flex items-center gap-1.5">
                  <span>🗺️</span>
                  <span>Watershed Map</span>
                </Link>
                <Link href="/ingest" className="px-3 py-1.5 rounded-lg text-[#C3B8DF] hover:text-white hover:bg-[#221C3A] transition-colors flex items-center gap-1.5">
                  <span>📡</span>
                  <span>DRISHTI Ingestion</span>
                </Link>
                <Link href="/review-queue" className="px-3 py-1.5 rounded-lg text-[#C3B8DF] hover:text-white hover:bg-[#221C3A] transition-colors flex items-center gap-1.5">
                  <span>🔍</span>
                  <span>Review Queue</span>
                </Link>
                <Link href="/feasibility" className="px-3 py-1.5 rounded-lg text-[#C3B8DF] hover:text-white hover:bg-[#221C3A] transition-colors flex items-center gap-1.5">
                  <span>📊</span>
                  <span>DPR Feasibility</span>
                </Link>
              </div>
            </div>
          </nav>
          <div className="flex-1 flex flex-col">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}
