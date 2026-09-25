"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ReviewRouting } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardTitle, CardDescription } from "@/components/ui/card";
import { FadeIn } from "@/components/ui/fade-in";
import { AlertTriangle, ArrowLeft, Filter, Layers, UserCheck } from "lucide-react";

const ROLE_DISPLAY_NAMES: Record<string, string> = {
  water_management: "Water Management",
  agriculture: "Agriculture",
  soil_science: "Soil Science",
  social_mobilization: "Social Mobilization",
  committee_member: "Watershed Committee",
};

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewRouting[]>([]);
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .reviewQueue(roleFilter || undefined)
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [roleFilter]);

  const roles = ["water_management", "agriculture", "soil_science", "social_mobilization", "committee_member"];

  const getStatusBadgeVariant = (status?: string | null) => {
    switch (status?.toLowerCase()) {
      case "confirmed":
        return "confirmed";
      case "rainfall_confounded":
        return "confounded";
      case "disagreement":
        return "disagreement";
      default:
        return "no_evidence";
    }
  };

  return (
    <div className="min-h-screen bg-[#0D0A18] text-[#F3F0FA] font-sans pb-16">
      {/* Top Header Nav */}
      <header className="border-b border-[#A997DF]/15 bg-[#161226]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link href="/">
              <Button variant="ghost" size="sm" className="text-[#C3B8DF] hover:text-white">
                <ArrowLeft className="w-4 h-4 mr-1" /> Home
              </Button>
            </Link>
            <span className="text-[#A997DF]/30">|</span>
            <span className="text-sm font-bold lavender-gradient-text flex items-center">
              <UserCheck className="w-4 h-4 mr-2 text-[#A997DF]" /> Specialist Triage Queue
            </span>
          </div>
          <Link href="/assets">
            <Button variant="outline" size="sm" className="border-[#A997DF]/30 text-[#DCCFEC] hover:bg-[#221C3A]">
              <Layers className="w-4 h-4 mr-2 text-[#A997DF]" /> Live 3D Map
            </Button>
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
        
        {/* Banner Section */}
        <FadeIn direction="up">
          <div className="rounded-2xl bg-gradient-to-r from-[#1F1A34] via-[#161226] to-[#1F1A34] border border-[#A997DF]/30 p-6 sm:p-8 shadow-2xl space-y-3">
            <div className="flex items-center space-x-2 text-[#A997DF] text-xs font-mono uppercase tracking-wider font-bold">
              <span>📋 Targeted Audit Workflow</span>
              <span>•</span>
              <span>Domain Specialist Queue</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight lavender-gradient-text">
              Targeted Specialist Review Queue
            </h1>
            <p className="text-xs sm:text-sm text-[#C3B8DF]/80 max-w-3xl leading-relaxed">
              Flagged watershed assets requiring domain-expert review. Each asset is deterministically routed based on visual features, telemetry disagreement, or historical rainfall baseline anomalies.
            </p>
          </div>
        </FadeIn>

        {/* Role Filter Pills Bar */}
        <FadeIn direction="up" delay={0.1}>
          <div className="flex items-center gap-2 flex-wrap bg-[#161226]/80 p-3 rounded-2xl border border-[#A997DF]/20 backdrop-blur-md">
            <span className="text-xs font-bold text-[#C3B8DF] px-2 flex items-center">
              <Filter className="w-3.5 h-3.5 mr-1 text-[#A997DF]" /> Filter by Role:
            </span>
            <button
              onClick={() => setRoleFilter("")}
              className={`text-xs px-3.5 py-1.5 rounded-xl font-bold transition-all cursor-pointer ${
                !roleFilter
                  ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md"
                  : "bg-[#221C3A] text-[#C3B8DF] hover:text-white hover:bg-[#2D264A]"
              }`}
            >
              All Roles
            </button>

            {roles.map((r) => (
              <button
                key={r}
                onClick={() => setRoleFilter(r)}
                className={`text-xs px-3.5 py-1.5 rounded-xl font-bold transition-all cursor-pointer ${
                  roleFilter === r
                    ? "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md"
                    : "bg-[#221C3A] text-[#C3B8DF] hover:text-white hover:bg-[#2D264A]"
                }`}
              >
                {ROLE_DISPLAY_NAMES[r] ?? r}
              </button>
            ))}
          </div>
        </FadeIn>

        {error && (
          <div className="bg-red-950/60 border border-red-500/40 text-red-200 text-sm p-4 rounded-xl">
            <strong>Could not load review queue:</strong> {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="h-24 bg-[#161226]/60 rounded-xl border border-[#A997DF]/15 animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 && !error ? (
          <FadeIn direction="up">
            <Card className="bg-[#161226]/80 border-[#A997DF]/20 p-12 text-center space-y-3">
              <span className="text-4xl">🎉</span>
              <CardTitle className="text-lg text-[#F3F0FA]">No Flagged Assets Pending Review</CardTitle>
              <CardDescription className="text-xs text-[#C3B8DF]/80 max-w-md mx-auto">
                All watershed assets under this specialist role are either confirmed or awaiting new field telemetry uploads.
              </CardDescription>
            </Card>
          </FadeIn>
        ) : (
          <div className="space-y-4">
            <div className="text-xs font-semibold text-[#C3B8DF] px-1 flex items-center justify-between">
              <span>Surfacing {items.length} flagged candidates needing specialist evaluation:</span>
            </div>

            {items.map((item, idx) => {
              const asset = item.asset;
              const role = asset.routed_role ?? "Unassigned";
              return (
                <FadeIn key={asset.id} direction="up" delay={idx * 0.05}>
                  <Card className="bg-[#161226]/80 border-[#A997DF]/20 hover:border-[#A997DF]/50 transition-all">
                    <CardContent className="p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-3 flex-wrap gap-y-1">
                          <span className="text-base font-bold text-[#F3F0FA]">{asset.project_id}</span>
                          <Badge variant={getStatusBadgeVariant(asset.triage_status)}>
                            {asset.triage_status?.toUpperCase() ?? "UNASSIGNED"}
                          </Badge>
                          <Badge variant="outline" className="text-xs border-[#A997DF]/30 text-[#DCCFEC]">
                            {ROLE_DISPLAY_NAMES[role] ?? role}
                          </Badge>
                        </div>

                        <div className="text-xs text-[#C3B8DF]/80 flex items-center space-x-4">
                          <span>District: <strong className="text-[#F3F0FA]">{asset.district}</strong></span>
                          <span>•</span>
                          <span>Confidence: <strong className="text-[#A997DF]">{Math.round((asset.confidence_score ?? 0) * 100)}%</strong></span>
                        </div>

                        {asset.disagreement_type && (
                          <div className="text-xs text-amber-300/90 flex items-center pt-1">
                            <AlertTriangle className="w-3.5 h-3.5 mr-1 flex-shrink-0" />
                            <span>Mismatch: {asset.disagreement_type}</span>
                          </div>
                        )}
                      </div>

                      <Link href={`/assets/${asset.id}`}>
                        <Button size="sm" className="bg-[#7058B6] hover:bg-[#8168C9] text-white shadow-md cursor-pointer flex items-center gap-1">
                          <span>Audit &amp; Review Candidate</span>
                          <span>&rarr;</span>
                        </Button>
                      </Link>
                    </CardContent>
                  </Card>
                </FadeIn>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
