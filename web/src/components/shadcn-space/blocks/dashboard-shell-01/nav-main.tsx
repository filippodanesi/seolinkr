"use client";

import { ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
} from "@/components/ui/sidebar";
import { NavItem } from "@/components/shadcn-space/blocks/dashboard-shell-01/app-sidebar";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavMain({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  const renderItem = (item: NavItem) => {
    // Section label
    if (item.isSection && item.label) {
      return (
        <SidebarGroup key={item.label} className="p-0 pt-5 first:pt-0">
          <SidebarGroupLabel className="p-0 text-xs font-medium uppercase text-sidebar-foreground">
            {item.label}
          </SidebarGroupLabel>
        </SidebarGroup>
      );
    }

    const hasChildren = !!item.children?.length;

    // Item with children → collapsible
    if (hasChildren && item.title) {
      const isChildActive = item.children!.some(
        (c) => pathname === c.href || pathname.startsWith((c.href ?? "") + "/")
      );

      return (
        <SidebarGroup key={item.title} className="p-0">
          <SidebarMenu>
            <Collapsible defaultOpen={isChildActive}>
              <SidebarMenuItem>
                <CollapsibleTrigger asChild>
                  <SidebarMenuButton
                    tooltip={item.title}
                    className="rounded-xl text-sm px-3 py-2 h-9"
                  >
                    {item.icon && <item.icon size={16} />}
                    <span>{item.title}</span>
                    <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                  </SidebarMenuButton>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <SidebarMenuSub className="me-0 pe-0">
                    {item.children!.map(renderSubItem)}
                  </SidebarMenuSub>
                </CollapsibleContent>
              </SidebarMenuItem>
            </Collapsible>
          </SidebarMenu>
        </SidebarGroup>
      );
    }

    // Leaf item
    if (item.title) {
      const isActive = pathname === item.href;

      return (
        <SidebarGroup key={item.title} className="p-0">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                tooltip={item.title}
                className={cn(
                  "rounded-lg text-sm px-3 py-2 h-9",
                  isActive &&
                    "bg-primary hover:bg-primary dark:bg-blue-500 text-white dark:hover:bg-blue-500 hover:text-white"
                )}
              >
                {item.icon && <item.icon size={16} />}
                <Link href={item.href ?? "#"} className="w-full">
                  {item.title}
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>
      );
    }

    return null;
  };

  const renderSubItem = (item: NavItem) => {
    const isActive = pathname === item.href;

    if (item.title) {
      return (
        <SidebarMenuSubItem key={item.title} className="w-full">
          <SidebarMenuSubButton
            asChild
            className={cn("w-full", isActive && "font-medium text-primary")}
          >
            <Link href={item.href ?? "#"}>{item.title}</Link>
          </SidebarMenuSubButton>
        </SidebarMenuSubItem>
      );
    }
    return null;
  };

  return <>{items.map(renderItem)}</>;
}
