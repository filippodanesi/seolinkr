// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useEffect, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listSitemaps } from "@/lib/api";

interface SitemapSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function SitemapSelector({ value, onChange }: SitemapSelectorProps) {
  const [saved, setSaved] = useState<Record<string, string>>({});
  const [useCustom, setUseCustom] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    listSitemaps()
      .then(setSaved)
      .catch(() => {});
  }, []);

  const entries = Object.entries(saved);

  // Find the display name for the currently selected URL
  const selectedName = entries.find(([, url]) => url === value)?.[0];

  if (entries.length === 0 || useCustom) {
    return (
      <div className="space-y-1.5">
        <Label>Sitemap URL(s)</Label>
        <Input
          placeholder="https://example.com/sitemap.xml"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        {entries.length > 0 && (
          <button
            type="button"
            className="text-xs text-muted-foreground underline"
            onClick={() => setUseCustom(false)}
          >
            Use saved sitemap
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <Label>Sitemap</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between font-normal"
          >
            <span className="truncate">
              {selectedName || "Select a sitemap..."}
            </span>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search sitemaps..." />
            <CommandList>
              <CommandEmpty>No sitemap found.</CommandEmpty>
              <CommandGroup>
                {entries.map(([name, url]) => (
                  <CommandItem
                    key={name}
                    value={name}
                    onSelect={() => {
                      onChange(url === value ? "" : url);
                      setOpen(false);
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === url ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {name}
                  </CommandItem>
                ))}
                <CommandItem
                  value="__custom__"
                  onSelect={() => {
                    setUseCustom(true);
                    onChange("");
                    setOpen(false);
                  }}
                >
                  Custom URL...
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
