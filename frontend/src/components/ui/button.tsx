import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "lavender" | "outline" | "ghost" | "destructive" | "secondary";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(
          "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 disabled:pointer-events-none disabled:opacity-50 active:scale-95 cursor-pointer",
          {
            "bg-gradient-to-r from-[#7058B6] to-[#5B44A0] text-white shadow-md hover:from-[#8168C9] hover:to-[#6A52B5] hover:shadow-purple-900/30":
              variant === "default" || variant === "lavender",
            "border border-[#A997DF]/30 bg-[#161226]/80 text-[#F3F0FA] hover:bg-[#221C3A] hover:border-[#A997DF]/60":
              variant === "outline",
            "bg-[#221C3A] text-[#DCCFEC] hover:bg-[#2D264A] hover:text-white":
              variant === "secondary",
            "hover:bg-[#A997DF]/15 text-[#C3B8DF] hover:text-white": variant === "ghost",
            "bg-red-600/90 text-white hover:bg-red-700 shadow-sm": variant === "destructive",
            "h-10 px-4 py-2": size === "default",
            "h-8 rounded-md px-3 text-xs": size === "sm",
            "h-12 rounded-xl px-6 text-base font-semibold": size === "lg",
            "h-9 w-9 p-0": size === "icon",
          },
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
