"use client";

import { usePathname } from "next/navigation";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

const breadcrumbMap: Record<string, { group: string; page: string }> = {
  "/process": { group: "Linking", page: "Process Article" },
  "/candidates": { group: "Linking", page: "Candidates" },
  "/audit": { group: "Linking", page: "Audit" },
  "/gsc/opportunities": { group: "GSC Intelligence", page: "Opportunities" },
  "/gsc/cross-gaps": { group: "GSC Intelligence", page: "Cross-Link Gaps" },
  "/settings": { group: "Settings", page: "Settings" },
};

export function SiteHeader() {
  const pathname = usePathname();
  const crumb = breadcrumbMap[pathname];

  return (
    <div className="flex w-full items-center">
      <div className="flex items-center gap-2">
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
      </div>
    </div>
  );
}
