"use client";

import React from "react";
import { motion } from "framer-motion";

export const BackgroundBeams = ({ className }: { className?: string }) => {
  return (
    <div
      className={`absolute inset-0 overflow-hidden [mask-image:radial-gradient(ellipse_at_center,transparent_20%,black)] pointer-events-none ${className}`}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-[#DDC4DD]/10 via-[#A997DF]/15 to-[#7058B6]/10 opacity-40 blur-3xl animate-pulse" />
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.6 }}
        transition={{ duration: 1.5 }}
        className="absolute -top-[40%] left-[20%] w-[600px] h-[600px] rounded-full bg-gradient-to-br from-[#A997DF]/20 to-purple-900/30 blur-[120px]"
      />
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        transition={{ duration: 2, delay: 0.5 }}
        className="absolute -bottom-[20%] right-[10%] w-[500px] h-[500px] rounded-full bg-gradient-to-tl from-[#DCCFEC]/20 to-indigo-900/20 blur-[100px]"
      />
    </div>
  );
};
