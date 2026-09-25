"use client";

import dynamic from "next/dynamic";
import React from "react";
import Link from "next/link";
import { ArrowLeft, Layers, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center text-[#F3F0FA] bg-[#0D0A18]">
      <div className="w-10 h-10 border-4 border-[#A997DF]/30 border-t-[#7058B6] rounded-full animate-spin mb-4" />
      <span className="text-sm font-semibold text-[#C3B8DF]">Initializing 3D GIS Watershed Map Engine...</span>
    </div>
  ),
});

export default function AssetsRootPage() {
  return (
    <div className="w-screen h-screen bg-[#0D0A18] text-[#F3F0FA] flex flex-col overflow-hidden">
      {/* Top Header Bar */}
      <header className="h-14 border-b border-[#A997DF]/15 bg-[#161226]/90 backdrop-blur-xl z-50 flex-shrink-0 px-4 sm:px-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link href="/">
            <Button variant="ghost" size="sm" className="text-[#C3B8DF] hover:text-white">
              <ArrowLeft className="w-4 h-4 mr-1" /> Home
            </Button>
          </Link>
          <span className="text-[#A997DF]/30">|</span>
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-[#A997DF]" />
            <span className="text-sm font-bold lavender-gradient-text">Interactive 3D GIS Watershed Map</span>
          </div>
        </div>

        <nav className="flex items-center space-x-3">
          <Link href="/review-queue">
            <Button variant="outline" size="sm" className="border-[#A997DF]/30 text-[#DCCFEC] hover:bg-[#221C3A]">
              <UserCheck className="w-4 h-4 mr-1.5 text-[#A997DF]" /> Review Queue
            </Button>
          </Link>
        </nav>
      </header>

      {/* Main Full-Screen Map Container */}
      <main className="flex-1 relative w-full h-[calc(100vh-3.5rem)] overflow-hidden">
        <MapView />
      </main>
    </div>
  );
}
