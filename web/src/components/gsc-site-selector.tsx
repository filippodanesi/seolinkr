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
import { listGscProperties } from "@/lib/api";

interface GscProperty {
  site_url: string;
  permission_level: string;
}

interface GscSiteSelectorProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

export function GscSiteSelector({
  value,
  onChange,
  label,
}: GscSiteSelectorProps) {
  const [open, setOpen] = useState(false);
  const [properties, setProperties] = useState<GscProperty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const props = await listGscProperties();
        if (cancelled) return;
        setProperties(props);
        setError("");
      } catch {
        if (cancelled) return;
        setError("GSC credentials not configured");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const placeholder = loading
    ? "Loading GSC properties..."
    : error
      ? error
      : "Select a GSC property...";

  const selectedLabel = properties.find((p) => p.site_url === value)?.site_url;

  return (
    <div className="space-y-1.5">
      {label && (
        <label className="text-sm font-medium leading-none">{label}</label>
      )}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={loading || !!error}
            className="w-full justify-between font-normal"
          >
            <span className="truncate">
              {selectedLabel || placeholder}
            </span>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search properties..." />
            <CommandList>
              <CommandEmpty>No property found.</CommandEmpty>
              <CommandGroup>
                {properties.map((p) => (
                  <CommandItem
                    key={p.site_url}
                    value={p.site_url}
                    onSelect={(v) => {
                      onChange(v === value ? "" : v);
                      setOpen(false);
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === p.site_url ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {p.site_url}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
