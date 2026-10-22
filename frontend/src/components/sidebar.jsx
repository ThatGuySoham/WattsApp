"use client"
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LineChart, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Household Dashboard", icon: Home },
    { href: "/analytics", label: "AI Analytics & Predictions", icon: LineChart },
  ];

  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      <div className="p-6 flex items-center gap-2 text-primary font-bold text-xl tracking-tight">
        <Zap className="size-6 fill-primary" />
        WattsApp
      </div>
      <nav className="flex-1 px-4 space-y-2">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <link.icon className={cn("size-5", active ? "text-primary" : "text-muted-foreground")} />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
