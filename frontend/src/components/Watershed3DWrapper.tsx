"use client";

import dynamic from "next/dynamic";
import React from "react";

const Watershed3DCanvas = dynamic(() => import("./Watershed3DCanvas"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[420px] md:h-[480px] rounded-2xl glass-panel flex flex-col items-center justify-center border border-[#A997DF]/20">
      <div className="w-10 h-10 border-4 border-[#A997DF]/30 border-t-[#7058B6] rounded-full animate-spin mb-3" />
      <span className="text-xs font-semibold text-[#C3B8DF]">Loading 3D Procedural Terrain Model...</span>
    </div>
  ),
});

export default function Watershed3DWrapper({
  activeStructureIndex,
  onSelectStructure,
}: {
  activeStructureIndex: number;
  onSelectStructure: (idx: number) => void;
}) {
  return <Watershed3DCanvas activeStructureIndex={activeStructureIndex} onSelectStructure={onSelectStructure} />;
}
