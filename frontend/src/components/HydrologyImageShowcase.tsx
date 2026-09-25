"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { ChevronLeft, ChevronRight, Sparkles } from "lucide-react";

export interface ShowcaseSlide {
  title: string;
  category: string;
  description: string;
  icon: string;
  imageSrc: string;
  badge: string;
}

export const SHOWCASE_SLIDES: ShowcaseSlide[] = [
  {
    title: "Earthen Farm Pond Asset",
    category: "Rainwater Harvesting & Storage",
    description: "Excavated agricultural storage pond with earthen bund embankments capturing surface runoff and recharging local groundwater.",
    icon: "🌊",
    imageSrc: "/showcase/farm_pond.jpg",
    badge: "Field Verified Asset",
  },
  {
    title: "Avon Arch Masonry Dam",
    category: "Structural Stream Check Dam",
    description: "Concrete arch dam structure with spillway crest, sluice gates, and energy dissipator stilling basin for stream flow retention.",
    icon: "🧱",
    imageSrc: "/showcase/check_dam.jpg",
    badge: "Hydraulic Structure",
  },
  {
    title: "Meandering River & Riparian Basin",
    category: "Sub-Watershed Hydrology",
    description: "Natural terraced river channel and wetland floodplain with stone percolation check steps for continuous baseflow recharge.",
    icon: "🏞️",
    imageSrc: "/showcase/river_wetland.jpg",
    badge: "Micro-Basin Channel",
  },
  {
    title: "Sentinel-2 & Bhuvan GIS Satellite",
    category: "Remote Sensing Telemetry",
    description: "Multispectral satellite constellation capturing 10-year RESTREND NDVI vegetation dynamics and Copernicus DEM slope elevation.",
    icon: "🛰️",
    imageSrc: "/showcase/gis_satellite.jpg",
    badge: "Spaceborne Telemetry",
  },
];

export default function HydrologyImageShowcase({
  activeSlideIndex,
  onSelectSlide,
}: {
  activeSlideIndex: number;
  onSelectSlide: (idx: number) => void;
}) {
  const [isHovered, setIsHovered] = useState(false);

  // Auto-cycle through slides every 4 seconds unless hovered
  useEffect(() => {
    if (isHovered) return;
    const timer = setInterval(() => {
      onSelectSlide((activeSlideIndex + 1) % SHOWCASE_SLIDES.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [activeSlideIndex, isHovered, onSelectSlide]);

  const currentSlide = SHOWCASE_SLIDES[activeSlideIndex];

  return (
    <div
      className="relative w-full h-[420px] md:h-[480px] rounded-2xl overflow-hidden bg-[#0D0A18] border border-[#A997DF]/35 shadow-2xl group select-none"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Background Image Carousel with Fading Cross-Dissolve */}
      {SHOWCASE_SLIDES.map((slide, idx) => {
        const isActive = idx === activeSlideIndex;
        return (
          <div
            key={slide.title}
            className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${
              isActive ? "opacity-100 z-10 scale-100" : "opacity-0 z-0 pointer-events-none scale-105"
            } transform transition-transform duration-7000 ease-out`}
          >
            <Image
              src={slide.imageSrc}
              alt={slide.title}
              fill
              priority={idx === 0}
              className="object-cover object-center filter brightness-[0.88] contrast-[1.05]"
            />
            {/* Dark Vignette Gradients for Legibility */}
            <div className="absolute inset-0 bg-gradient-to-t from-[#0D0A18] via-[#0D0A18]/30 to-black/50" />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0D0A18]/70 via-transparent to-transparent" />
          </div>
        );
      })}

      {/* Top Floating Telemetry Badges */}
      <div className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 bg-[#161226]/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-[#A997DF]/30 shadow-lg pointer-events-auto">
          <span className="text-base">{currentSlide.icon}</span>
          <span className="text-xs font-bold text-[#F3F0FA] font-sans">{currentSlide.category}</span>
        </div>

        <div className="flex items-center gap-1.5 bg-[#7058B6]/30 backdrop-blur-md text-[#DCCFEC] px-3 py-1.5 rounded-xl border border-[#A997DF]/40 text-xs font-semibold shadow-lg pointer-events-auto">
          <Sparkles className="w-3.5 h-3.5 text-purple-300 animate-pulse" />
          <span>{currentSlide.badge}</span>
        </div>
      </div>

      {/* Prev / Next Arrow Navigation Controls */}
      <button
        type="button"
        onClick={() => onSelectSlide((activeSlideIndex - 1 + SHOWCASE_SLIDES.length) % SHOWCASE_SLIDES.length)}
        className="absolute left-3 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full bg-[#161226]/80 text-[#F3F0FA] hover:bg-[#7058B6] border border-[#A997DF]/40 flex items-center justify-center backdrop-blur-md opacity-0 group-hover:opacity-100 transition-all cursor-pointer shadow-xl"
        aria-label="Previous Slide"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      <button
        type="button"
        onClick={() => onSelectSlide((activeSlideIndex + 1) % SHOWCASE_SLIDES.length)}
        className="absolute right-3 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full bg-[#161226]/80 text-[#F3F0FA] hover:bg-[#7058B6] border border-[#A997DF]/40 flex items-center justify-center backdrop-blur-md opacity-0 group-hover:opacity-100 transition-all cursor-pointer shadow-xl"
        aria-label="Next Slide"
      >
        <ChevronRight className="w-5 h-5" />
      </button>

      {/* Bottom Floating Selector Pills */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center space-x-1.5 bg-[#161226]/95 backdrop-blur-md px-3 py-1.5 rounded-full border border-[#A997DF]/35 shadow-2xl z-20 max-w-[95%] overflow-x-auto">
        {SHOWCASE_SLIDES.map((slide, idx) => {
          const isActive = idx === activeSlideIndex;
          return (
            <button
              key={slide.title}
              type="button"
              onClick={() => onSelectSlide(idx)}
              className={`px-3 py-1 text-xs font-bold rounded-full transition-all cursor-pointer flex items-center gap-1.5 shrink-0 ${
                isActive
                  ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md border border-purple-400/50 scale-105"
                  : "text-[#C3B8DF] hover:text-white hover:bg-[#221C3A]"
              }`}
            >
              <span>{slide.icon}</span>
              <span>{slide.title.split(" ")[0]}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
