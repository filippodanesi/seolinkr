"use client";

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { NavItem } from "@/components/shadcn-space/blocks/dashboard-shell-01/app-sidebar";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavMain({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  // Group items by section
  const sections: { label: string; items: NavItem[] }[] = [];
  let current: { label: string; items: NavItem[] } | null = null;

  for (const item of items) {
    if (item.isSection && item.label) {
      current = { label: item.label, items: [] };
      sections.push(current);
    } else if (current) {
      current.items.push(item);
    }
  }

  return (
    <div className="flex flex-col gap-0">
      {sections.map((section, idx) => (
        <SidebarGroup
          key={section.label}
          className={cn("p-0 pt-4", idx > 0 && "mt-4 border-t border-border pt-4")}
        >
          <SidebarGroupLabel className="p-0 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            {section.label}
          </SidebarGroupLabel>
          <SidebarMenu>
            {section.items.map((item) => {
              const isActive = pathname === item.href;
              return (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    asChild
                    className={cn(
                      "rounded-md text-sm px-3 py-2 h-9",
                      isActive && "bg-accent font-medium"
                    )}
                  >
                    <Link href={item.href ?? "#"}>{item.title}</Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>
      ))}
    </div>
  );
}
