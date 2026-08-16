import { cn } from "@/lib/utils";

export interface BadgeProps {
  variant?: "default" | "destructive" | "outline" | "secondary";
  className?: string;
  children: React.ReactNode;
}

export function Badge({ variant = "default", className, children }: BadgeProps) {
  const base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors";
  
  const variants = {
    default: "bg-primary/10 text-primary border border-primary/20",
    destructive: "bg-destructive/10 text-destructive border border-destructive/20",
    outline: "border border-white/10 text-text-1",
    secondary: "bg-white/5 text-text-1 border border-white/10",
  };

  return (
    <span className={cn(base, variants[variant], className)}>
      {children}
    </span>
  );
}