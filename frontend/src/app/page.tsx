"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { FadeIn } from "@/components/ui/fade-in";
import { BackgroundBeams } from "@/components/ui/background-beams";
import HydrologyImageShowcase, { SHOWCASE_SLIDES } from "@/components/HydrologyImageShowcase";
import { CountingNumber } from "@/components/ui/CountingNumber";
import {
  Map,
  CheckCircle2,
  FileText,
  Activity,
  Layers,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Compass,
  Cpu,
  BarChart3
} from "lucide-react";

export default function LandingPage() {
  const [activeSlide, setActiveSlide] = useState<number>(0);

  const currentSlide = SHOWCASE_SLIDES[activeSlide];

  return (
    <div className="min-h-screen bg-[#0D0A18] text-[#F3F0FA] relative overflow-hidden font-sans">
      {/* Aceternity Glowing Beams Background */}
      <BackgroundBeams />

      {/* Header Navigation */}
      <header className="relative z-50 border-b border-[#A997DF]/15 bg-[#161226]/80 backdrop-blur-xl sticky top-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#7058B6] to-[#A997DF] flex items-center justify-center shadow-lg shadow-purple-900/30">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-extrabold tracking-tight lavender-gradient-text">Satmaps</span>
              <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded-full bg-[#A997DF]/15 text-[#DCCFEC] border border-[#A997DF]/30 font-medium">
                PS 26015
              </span>
            </div>
          </div>

          <nav className="flex items-center space-x-3">
            <Link href="/assets">
              <Button variant="outline" size="sm" className="hidden sm:inline-flex border-[#A997DF]/30 text-[#DCCFEC] hover:bg-[#221C3A]">
                <Map className="w-4 h-4 mr-2 text-[#A997DF]" /> Live Map
              </Button>
            </Link>
            <Link href="/review-queue">
              <Button variant="default" size="sm" className="bg-gradient-to-r from-[#7058B6] to-[#5B44A0] hover:from-[#8168C9] hover:to-[#6A52B5] shadow-md">
                <CheckCircle2 className="w-4 h-4 mr-2" /> Expert Triage Queue
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Hero Text Column */}
          <div className="lg:col-span-6 space-y-6">
            <FadeIn direction="up" delay={0.1}>
              <Badge variant="outline" className="px-3 py-1 text-xs border-[#A997DF]/40 bg-[#1F1A34]/80 text-[#DCCFEC] backdrop-blur-md">
                <Sparkles className="w-3.5 h-3.5 mr-1.5 text-purple-400" /> Integrated GIS &amp; AI Remote Sensing Platform
              </Badge>
            </FadeIn>

            <FadeIn direction="up" delay={0.2}>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1] lavender-gradient-text">
                Systematic Watershed Impact Verification
              </h1>
            </FadeIn>

            <FadeIn direction="up" delay={0.3}>
              <p className="text-base sm:text-lg text-[#C3B8DF]/90 leading-relaxed">
                Transforming static geo-coded field photographs into multi-layered spatial evidence. Combining Sentinel-2 multispectral imagery, Landsat 8 10-year RESTREND trend regression, D8 stream ordering, and OpenAI CLIP zero-shot neural visual interpretation.
              </p>
            </FadeIn>

            <FadeIn direction="up" delay={0.4}>
              <div className="flex flex-wrap items-center gap-4 pt-2">
                <Link href="/assets">
                  <Button size="lg" className="bg-gradient-to-r from-[#7058B6] to-[#5B44A0] hover:from-[#8168C9] hover:to-[#6A52B5] text-white shadow-xl shadow-purple-900/40 cursor-pointer">
                    Explore Interactive 3D Map <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link href="/review-queue">
                  <Button variant="outline" size="lg" className="border-[#A997DF]/40 text-[#F3F0FA] hover:bg-[#221C3A] cursor-pointer">
                    View Review Queue
                  </Button>
                </Link>
              </div>
            </FadeIn>

            {/* Quick Metrics Banner */}
            <FadeIn direction="up" delay={0.5}>
              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-[#A997DF]/15">
                <div>
                  <CountingNumber
                    end={358}
                    suffix="+"
                    className="text-2xl sm:text-3xl font-extrabold text-[#F3F0FA] tracking-tight"
                  />
                  <div className="text-xs text-[#C3B8DF]/70 font-medium mt-0.5">Verified Assets</div>
                </div>
                <div>
                  <CountingNumber
                    end={1514}
                    className="text-2xl sm:text-3xl font-extrabold text-[#A997DF] tracking-tight"
                  />
                  <div className="text-xs text-[#C3B8DF]/70 font-medium mt-0.5">EXIF Field Photos</div>
                </div>
                <div>
                  <CountingNumber
                    end={10}
                    suffix="-Year"
                    className="text-2xl sm:text-3xl font-extrabold text-emerald-400 tracking-tight"
                  />
                  <div className="text-xs text-[#C3B8DF]/70 font-medium mt-0.5">RESTREND Baseline</div>
                </div>
              </div>
            </FadeIn>
          </div>

          {/* Right Floating Fading Image Showcase Column */}
          <div className="lg:col-span-6">
            <FadeIn direction="up" delay={0.3}>
              <div className="space-y-4">
                {/* Fading Image Showcase Carousel */}
                <HydrologyImageShowcase
                  activeSlideIndex={activeSlide}
                  onSelectSlide={(idx) => setActiveSlide(idx)}
                />

                {/* Structure / Telemetry Details Card */}
                <Card className="bg-[#161226]/90 border-[#A997DF]/30 backdrop-blur-xl">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg text-[#DCCFEC] flex items-center gap-2">
                        <span>{currentSlide.icon}</span>
                        <span>{currentSlide.title}</span>
                      </CardTitle>
                      <Badge variant="outline" className="text-xs border-[#A997DF]/30 text-[#A997DF]">
                        Feature #{activeSlide + 1} of 4
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-xs sm:text-sm text-[#C3B8DF]/80">
                      {currentSlide.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </div>
            </FadeIn>
          </div>
        </div>

        {/* Feature Capabilities Grid */}
        <div className="mt-24">
          <FadeIn direction="up" delay={0.2}>
            <div className="text-center max-w-3xl mx-auto mb-12">
              <Badge variant="outline" className="mb-3 border-[#A997DF]/30 text-[#DCCFEC]">
                Scientific Framework Architecture
              </Badge>
              <h2 className="text-3xl sm:text-4xl font-extrabold lavender-gradient-text">
                Multi-Layered Spatial Evidence Pipeline
              </h2>
              <p className="mt-3 text-sm sm:text-base text-[#C3B8DF]/80">
                End-to-end integration addressing the central requirements of SIH PS 26015.
              </p>
            </div>
          </FadeIn>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* Feature 1 */}
            <FadeIn direction="up" delay={0.1}>
              <Card className="h-full bg-[#161226]/70 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all hover:translate-y-[-2px]">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-[#A997DF]/15 flex items-center justify-center mb-2">
                    <Cpu className="w-5 h-5 text-purple-400" />
                  </div>
                  <CardTitle className="text-base text-[#F3F0FA]">CLIP Visual Feature Similarity</CardTitle>
                  <CardDescription className="text-xs text-[#C3B8DF]/80">
                    Zero-shot OpenAI CLIP (ViT-B/32) embeddings parsing ground photographs into structural element similarities.
                  </CardDescription>
                </CardHeader>
              </Card>
            </FadeIn>

            {/* Feature 2 */}
            <FadeIn direction="up" delay={0.2}>
              <Card className="h-full bg-[#161226]/70 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all hover:translate-y-[-2px]">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-emerald-950/60 flex items-center justify-center mb-2">
                    <BarChart3 className="w-5 h-5 text-emerald-400" />
                  </div>
                  <CardTitle className="text-base text-[#F3F0FA]">10-Year RESTREND Analysis</CardTitle>
                  <CardDescription className="text-xs text-[#C3B8DF]/80">
                    OLS linear regression of Landsat-8 NDVI vs IMD precipitation, isolating intervention impact from natural rainfall variance.
                  </CardDescription>
                </CardHeader>
              </Card>
            </FadeIn>

            {/* Feature 3 */}
            <FadeIn direction="up" delay={0.3}>
              <Card className="h-full bg-[#161226]/70 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all hover:translate-y-[-2px]">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-blue-950/60 flex items-center justify-center mb-2">
                    <Compass className="w-5 h-5 text-blue-400" />
                  </div>
                  <CardTitle className="text-base text-[#F3F0FA]">D8 Hydrological Stream Engine</CardTitle>
                  <CardDescription className="text-xs text-[#C3B8DF]/80">
                    Copernicus DEM 30m flow direction, accumulation, Strahler stream ordering, and automated catchment delineation.
                  </CardDescription>
                </CardHeader>
              </Card>
            </FadeIn>

            {/* Feature 4 */}
            <FadeIn direction="up" delay={0.4}>
              <Card className="h-full bg-[#161226]/70 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all hover:translate-y-[-2px]">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-purple-950/60 flex items-center justify-center mb-2">
                    <Activity className="w-5 h-5 text-purple-300" />
                  </div>
                  <CardTitle className="text-base text-[#F3F0FA]">Differential Δ Change Maps</CardTitle>
                  <CardDescription className="text-xs text-[#C3B8DF]/80">
                    Quantitative ΔNDVI, ΔNDWI, and SMI Soil Moisture Proxy rasters calculated between pre/post satellite scenes.
                  </CardDescription>
                </CardHeader>
              </Card>
            </FadeIn>

            {/* Feature 5 */}
            <FadeIn direction="up" delay={0.5}>
              <Card className="h-full bg-[#161226]/70 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all hover:translate-y-[-2px]">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-orange-950/60 flex items-center justify-center mb-2">
                    <ShieldCheck className="w-5 h-5 text-orange-400" />
                  </div>
                  <CardTitle className="text-base text-[#F3F0FA]">4-State Triage & Domain Routing</CardTitle>
                  <CardDescription className="text-xs text-[#C3B8DF]/80">
                    Rule-based classification routing cases to Hydrologists, Agronomists, Soil Experts, or Civil Engineers.
                  </CardDescription>
                </CardHeader>
              </Card>
            </FadeIn>

            {/* Feature 6 */}
            <FadeIn direction="up" delay={0.6}>
              <Card className="h-full bg-[#161226]/70 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all hover:translate-y-[-2px]">
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-pink-950/60 flex items-center justify-center mb-2">
                    <FileText className="w-5 h-5 text-pink-400" />
                  </div>
                  <CardTitle className="text-base text-[#F3F0FA]">PDF Evidence Packets</CardTitle>
                  <CardDescription className="text-xs text-[#C3B8DF]/80">
                    Automated generation of audit-ready PDF reports compiling satellite maps, trend graphs, and expert reviews.
                  </CardDescription>
                </CardHeader>
              </Card>
            </FadeIn>
          </div>
        </div>

        {/* Provenance Integrity Banner */}
        <div className="mt-20">
          <FadeIn direction="up" delay={0.2}>
            <div className="rounded-2xl bg-gradient-to-r from-[#1F1A34] via-[#161226] to-[#1F1A34] border border-[#A997DF]/30 p-8 shadow-2xl relative overflow-hidden">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <span className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Scientific Data Provenance</span>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-[#F3F0FA]">
                    Verbatim Ground-Truth & Anti-Fabrication Pipeline
                  </h3>
                  <p className="text-xs sm:text-sm text-[#C3B8DF]/80 max-w-2xl">
                    Every ground photograph and metadata record is directly ingested from the verified <code>abc/</code> dataset. Zero synthetic labels or hardcoded overrides.
                  </p>
                </div>
                <Link href="/assets">
                  <Button className="bg-gradient-to-r from-[#7058B6] to-[#A997DF] text-white hover:opacity-90 whitespace-nowrap shadow-lg">
                    Launch Interactive Map System
                  </Button>
                </Link>
              </div>
            </div>
          </FadeIn>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[#A997DF]/15 bg-[#0D0A18] py-8 text-center text-xs text-[#C3B8DF]/60">
        <div className="max-w-7xl mx-auto px-4">
          <p>Satmaps Geospatial Monitoring Platform — Developed for SIH Problem Statement 26015</p>
          <p className="mt-1 text-[#8E82B4]">Automated decision-support system for watershed impact verification.</p>
        </div>
      </footer>
    </div>
  );
}
