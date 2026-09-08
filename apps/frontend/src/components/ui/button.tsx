import React from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "secondary" | "danger" | "destructive" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
}

export function Button({ className, variant = "default", size = "md", children, ...props }: ButtonProps) {
  const variants = {
    default: "bg-purple-600 hover:bg-purple-700 text-white",
    primary: "bg-purple-600 hover:bg-purple-700 text-white",
    secondary: "bg-white/10 hover:bg-white/15 text-white border border-white/10",
    danger: "bg-red-600 hover:bg-red-700 text-white",
    destructive: "bg-red-600 hover:bg-red-700 text-white",
    outline: "border border-gray-600 text-gray-300 hover:bg-gray-800",
    ghost: "text-gray-400 hover:text-white hover:bg-white/5",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg",
  };

  return (
    <button
      className={cn(
        "rounded-lg font-medium transition-all duration-200",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        "flex items-center gap-2",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
