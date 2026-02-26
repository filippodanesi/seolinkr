"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listSitemaps } from "@/lib/api";

interface SitemapSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function SitemapSelector({ value, onChange }: SitemapSelectorProps) {
  const [saved, setSaved] = useState<Record<string, string>>({});
  const [useCustom, setUseCustom] = useState(false);

  useEffect(() => {
    listSitemaps()
      .then(setSaved)
      .catch(() => {});
  }, []);

  const entries = Object.entries(saved);

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
      <Select
        value={value}
        onValueChange={(v) => {
          if (v === "__custom__") {
            setUseCustom(true);
            onChange("");
          } else {
            onChange(v);
          }
        }}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select a sitemap" />
        </SelectTrigger>
        <SelectContent>
          {entries.map(([name, url]) => (
            <SelectItem key={name} value={url}>
              {name}
            </SelectItem>
          ))}
          <SelectItem value="__custom__">Custom URL...</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
