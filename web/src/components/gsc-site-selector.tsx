// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

  if (loading) {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="text-sm font-medium leading-none">{label}</label>
        )}
        <Select disabled>
          <SelectTrigger>
            <SelectValue placeholder="Loading GSC properties..." />
          </SelectTrigger>
        </Select>
      </div>
    );
  }

  if (error || properties.length === 0) {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="text-sm font-medium leading-none">{label}</label>
        )}
        <Select disabled>
          <SelectTrigger>
            <SelectValue
              placeholder={error || "No GSC properties available"}
            />
          </SelectTrigger>
        </Select>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {label && (
        <label className="text-sm font-medium leading-none">{label}</label>
      )}
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder="Select a GSC property" />
        </SelectTrigger>
        <SelectContent>
          {properties.map((p) => (
            <SelectItem key={p.site_url} value={p.site_url}>
              {p.site_url}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
