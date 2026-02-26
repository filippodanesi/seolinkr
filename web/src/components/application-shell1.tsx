"use client";

import {
  CheckCircle2,
  ChevronRight,
  FileSearch,
  Link2,
  Search,
  Settings,
  TrendingUp,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";

import { cn } from "@/lib/utils";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// ── Navigation data ──────────────────────────────────────────

type NavItem = {
  label: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  href: string;
  children?: NavItem[];
};

type NavGroup = {
  title: string;
  items: NavItem[];
  defaultOpen?: boolean;
};

const navGroups: NavGroup[] = [
  {
    title: "Linking",
    defaultOpen: true,
    items: [
      { label: "Process Article", icon: Zap, href: "/process" },
      { label: "Candidates", icon: Search, href: "/candidates" },
      { label: "Audit", icon: CheckCircle2, href: "/audit" },
    ],
  },
  {
    title: "GSC Intelligence",
    defaultOpen: true,
    items: [
      {
        label: "Google Search Console",
        icon: TrendingUp,
        href: "/gsc",
        children: [
          { label: "Opportunities", icon: TrendingUp, href: "/gsc/opportunities" },
          { label: "Cross-Link Gaps", icon: Link2, href: "/gsc/cross-gaps" },
        ],
      },
    ],
  },
];

const footerItems: NavItem[] = [
  { label: "Settings", icon: Settings, href: "/settings" },
];

// ── Breadcrumb mapping ───────────────────────────────────────

const breadcrumbMap: Record<string, { group: string; page: string }> = {
  "/process": { group: "Linking", page: "Process Article" },
  "/candidates": { group: "Linking", page: "Candidates" },
  "/audit": { group: "Linking", page: "Audit" },
  "/gsc/opportunities": { group: "GSC Intelligence", page: "Opportunities" },
  "/gsc/cross-gaps": { group: "GSC Intelligence", page: "Cross-Link Gaps" },
  "/settings": { group: "Settings", page: "Settings" },
};

// ── Components ───────────────────────────────────────────────

function NavMenuItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const Icon = item.icon;
  const hasChildren = item.children && item.children.length > 0;
  const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

  if (!hasChildren) {
    return (
      <SidebarMenuItem>
        <SidebarMenuButton asChild isActive={isActive}>
          <Link href={item.href}>
            <Icon className="size-4" />
            <span>{item.label}</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  }

  const isChildActive = item.children!.some(
    (c) => pathname === c.href || pathname.startsWith(c.href + "/")
  );

  return (
    <Collapsible asChild defaultOpen={isActive || isChildActive} className="group/collapsible">
      <SidebarMenuItem>
        <CollapsibleTrigger asChild>
          <SidebarMenuButton isActive={isActive || isChildActive}>
            <Icon className="size-4" />
            <span>{item.label}</span>
            <ChevronRight className="ml-auto size-4 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
          </SidebarMenuButton>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarMenuSub>
            {item.children!.map((child) => (
              <SidebarMenuSubItem key={child.href}>
                <SidebarMenuSubButton asChild isActive={pathname === child.href}>
                  <Link href={child.href}>{child.label}</Link>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            ))}
          </SidebarMenuSub>
        </CollapsibleContent>
      </SidebarMenuItem>
    </Collapsible>
  );
}

function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();

  return (
    <Sidebar {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/process">
                <div className="flex aspect-square size-8 items-center justify-center rounded-sm bg-primary">
                  <FileSearch className="size-5 text-primary-foreground" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-medium">SEO Linker</span>
                  <span className="text-xs text-muted-foreground">v0.4.0</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent className="overflow-hidden">
        <ScrollArea className="min-h-0 flex-1">
          {navGroups.map((group) => (
            <SidebarGroup key={group.title}>
              <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.items.map((item) => (
                    <NavMenuItem key={item.href} item={item} pathname={pathname} />
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}
        </ScrollArea>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          {footerItems.map((item) => {
            const Icon = item.icon;
            return (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton asChild isActive={pathname === item.href}>
                  <Link href={item.href}>
                    <Icon className="size-4" />
                    <span>{item.label}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

// ── Shell ─────────────────────────────────────────────────────

interface ApplicationShellProps {
  children: React.ReactNode;
  className?: string;
}

export function ApplicationShell({ children, className }: ApplicationShellProps) {
  const pathname = usePathname();
  const crumb = breadcrumbMap[pathname];

  return (
    <SidebarProvider className={cn(className)}>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator
            orientation="vertical"
            className="mr-2 hidden data-[orientation=vertical]:h-4 md:block"
          />
          {crumb && (
            <Breadcrumb className="hidden md:block">
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink href="#">{crumb.group}</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>{crumb.page}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          )}
        </header>
        <div className="flex flex-1 flex-col overflow-y-auto">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
