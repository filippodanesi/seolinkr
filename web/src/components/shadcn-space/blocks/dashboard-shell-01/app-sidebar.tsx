"use client";
import React from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar";
import Logo from "@/assets/logo/logo";
import { NavMain } from "@/components/shadcn-space/blocks/dashboard-shell-01/nav-main";
import {
  CheckCircle2,
  Link2,
  LucideIcon,
  Search,
  Settings,
  TrendingUp,
  Zap,
} from "lucide-react";
import { SiteHeader } from "@/components/shadcn-space/blocks/dashboard-shell-01/site-header";
import SimpleBar from "simplebar-react";
import "simplebar-react/dist/simplebar.min.css";
import Link from "next/link";
import { usePathname } from "next/navigation";

export type NavItem = {
  label?: string;
  isSection?: boolean;
  title?: string;
  icon?: LucideIcon;
  href?: string;
  children?: NavItem[];
  isActive?: boolean;
};

export const navData: NavItem[] = [
  { label: "Linking", isSection: true },
  { title: "Process Article", icon: Zap, href: "/process" },
  { title: "Candidates", icon: Search, href: "/candidates" },
  { title: "Audit", icon: CheckCircle2, href: "/audit" },

  { label: "GSC Intelligence", isSection: true },
  {
    title: "Google Search Console",
    icon: TrendingUp,
    children: [
      { title: "Opportunities", href: "/gsc/opportunities" },
      { title: "Cross-Link Gaps", href: "/gsc/cross-gaps" },
    ],
  },
];

const AppSidebar = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();

  return (
    <SidebarProvider>
      <Sidebar className="py-4 px-0 bg-background">
        <div className="flex flex-col gap-6 bg-background h-full">
          {/* Header */}
          <SidebarHeader className="py-0 px-4">
            <SidebarMenu>
              <SidebarMenuItem>
                <Link href="/process" className="w-full h-full">
                  <Logo />
                </Link>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarHeader>

          {/* Content */}
          <SidebarContent className="overflow-hidden gap-0 px-0 flex-1">
            <SimpleBar
              autoHide={true}
              className="h-full border-b border-border"
            >
              <div className="px-4">
                <NavMain items={navData} />
              </div>
            </SimpleBar>
          </SidebarContent>

          {/* Footer — Settings */}
          <SidebarFooter className="px-4 py-0">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  className={
                    pathname === "/settings"
                      ? "bg-accent font-medium rounded-md text-sm px-3 py-2 h-9"
                      : "rounded-md text-sm px-3 py-2 h-9"
                  }
                >
                  <Link href="/settings">
                    <Settings className="size-4" />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </div>
      </Sidebar>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-50 flex items-center border-b px-6 py-3 bg-background">
          <SiteHeader />
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </SidebarProvider>
  );
};

export default AppSidebar;
