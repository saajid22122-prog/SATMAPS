"use client";

import React, { useEffect, useRef, useState } from "react";
import { useInView } from "framer-motion";

interface CountingNumberProps {
  end: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  formatter?: (val: number) => string;
  className?: string;
}

export function CountingNumber({
  end,
  duration = 1.8,
  suffix = "",
  prefix = "",
  formatter,
  className = "",
}: CountingNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: false, amount: 0.2 });
  const [displayValue, setDisplayValue] = useState<number>(0);

  useEffect(() => {
    if (!isInView) {
      setDisplayValue(0);
      return;
    }

    let startTime: number | null = null;
    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      
      // Smooth ease-out cubic curve
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const currentVal = Math.floor(easeProgress * end);
      
      setDisplayValue(currentVal);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step);
      } else {
        setDisplayValue(end);
      }
    };

    animationFrameId = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isInView, end, duration]);

  const formattedStr = formatter
    ? formatter(displayValue)
    : displayValue.toLocaleString("en-US");

  return (
    <span ref={ref} className={className}>
      {prefix}
      {formattedStr}
      {suffix}
    </span>
  );
}
