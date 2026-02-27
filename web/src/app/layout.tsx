// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";
import AppSidebar from "@/components/shadcn-space/blocks/dashboard-shell-01/app-sidebar";
import { ServerWarmup } from "@/components/server-warmup";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SEO Internal Linker",
  description: "Automated SEO internal linking tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${jetbrainsMono.variable} antialiased`}>
        <TooltipProvider>
          <ServerWarmup>
            <AppSidebar>{children}</AppSidebar>
          </ServerWarmup>
        </TooltipProvider>
        <Toaster />
      </body>
    </html>
  );
}
