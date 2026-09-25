"use client";

import React from "react";
import { motion } from "framer-motion";

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
  direction?: "up" | "down" | "left" | "right" | "none";
  once?: boolean;
}

export function FadeIn({
  children,
  delay = 0,
  duration = 0.3,
  className = "",
  direction = "up",
  once = false,
}: FadeInProps) {
  const getDirections = () => {
    switch (direction) {
      case "up":
        return { y: 20, x: 0 };
      case "down":
        return { y: -20, x: 0 };
      case "left":
        return { x: 20, y: 0 };
      case "right":
        return { x: -20, y: 0 };
      case "none":
        return { x: 0, y: 0 };
    }
  };

  const initialOffset = getDirections();

  return (
    <motion.div
      initial={{ opacity: 0, ...initialOffset }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: once, amount: 0.15 }}
      exit={{ opacity: 0 }}
      transition={{
        duration: duration,
        delay: delay,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
