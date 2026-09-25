import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "confirmed" | "confounded" | "disagreement" | "no_evidence" | "outline";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2",
        {
          "border-transparent bg-[#7058B6] text-white shadow": variant === "default",
          "border-emerald-500/50 bg-emerald-950/80 text-emerald-300 font-bold shadow-emerald-950/40":
            variant === "confirmed",
          "border-purple-500/50 bg-purple-950/80 text-purple-300 font-bold shadow-purple-950/40":
            variant === "confounded",
          "border-orange-500/50 bg-orange-950/80 text-orange-300 font-bold shadow-orange-950/40":
            variant === "disagreement",
          "border-slate-500/50 bg-slate-900/80 text-slate-300 font-bold":
            variant === "no_evidence",
          "border-[#A997DF]/40 text-[#DCCFEC] bg-[#161226]/60": variant === "outline",
        },
        className
      )}
      {...props}
    />
  );
}

export { Badge };
