// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { OctagonX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GscSiteSelector } from "@/components/gsc-site-selector";
import { PipelineProgress } from "@/components/pipeline-progress";
import { runLinkMap } from "@/lib/api";
import type { LinkMapResult, LinkMapSSEEvent } from "@/lib/types";

export default function LinkMapPage() {
  const [gscSite, setGscSite] = useState("");
  const [urlPattern, setUrlPattern] = useState("");
  const [urls, setUrls] = useState("");
  const [urlsFile, setUrlsFile] = useState<File | null>(null);
  const [days, setDays] = useState(90);
  const [minShared, setMinShared] = useState(1);

  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<LinkMapResult | null>(null);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function handleGenerate() {
    if (!gscSite) return;
    setRunning(true);
    setLogs([]);
    setResult(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runLinkMap(
        gscSite,
        {
          urls: urls || undefined,
          urlsFile: urlsFile || undefined,
          urlPattern: urlPattern || undefined,
          days,
          minShared,
          signal: controller.signal,
        },
        (event: LinkMapSSEEvent) => {
          if (event.type === "log") {
            setLogs((prev) => [...prev, event.message]);
          } else if (event.type === "result") {
            setResult(event.data);
          } else if (event.type === "error") {
            toast.error(event.message);
          }
        },
        () => setRunning(false)
      );
    } catch (e) {
      if (!controller.signal.aborted) {
        toast.error(String(e));
      }
      setRunning(false);
    } finally {
      abortRef.current = null;
    }
  }

  function handleDownload() {
    if (!result?.output_base64 || !result?.output_filename) return;
    const byteString = atob(result.output_base64);
    const bytes = new Uint8Array(byteString.length);
    for (let i = 0; i < byteString.length; i++) {
      bytes[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([bytes], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.output_filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  const priorityColors: Record<string, string> = {
    critical: "bg-red-100 text-red-800",
    high: "bg-orange-100 text-orange-800",
    medium: "bg-yellow-100 text-yellow-800",
    low: "bg-green-100 text-green-800",
  };

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardContent className="space-y-4 p-6">
          <div>
            <h2 className="text-lg font-semibold mb-1">Link Map</h2>
            <p className="text-sm text-muted-foreground">
              Generate strategic internal link recommendations based on GSC
              query overlap. Outputs which pages should link to which.
            </p>
          </div>

          <GscSiteSelector
            label="GSC Site"
            value={gscSite}
            onChange={setGscSite}
          />

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>URL Pattern (regex)</Label>
              <Input
                placeholder="e.g. /collections/|/magazine/"
                value={urlPattern}
                onChange={(e) => setUrlPattern(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Or paste URLs (comma-separated)</Label>
              <Input
                placeholder="https://example.com/page1, https://..."
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Or upload URL file</Label>
              <Input
                type="file"
                accept=".xlsx,.txt,.csv"
                onChange={(e) => setUrlsFile(e.target.files?.[0] || null)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Days</Label>
                <Input
                  type="number"
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Min Shared Queries</Label>
                <Input
                  type="number"
                  value={minShared}
                  onChange={(e) => setMinShared(Number(e.target.value))}
                />
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleGenerate}
              disabled={!gscSite || running}
            >
              {running ? "Generating..." : "Generate Link Map"}
            </Button>
            {running && (
              <Button variant="destructive" onClick={() => abortRef.current?.abort()}>
                <OctagonX className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <PipelineProgress logs={logs} isRunning={running} />

      {result && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">
                {result.total_recommendations} recommendations for{" "}
                {result.total_urls} URLs
              </h3>
              {result.output_base64 && (
                <Button variant="outline" size="sm" onClick={handleDownload}>
                  Download XLSX
                </Button>
              )}
            </div>

            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-background border-b">
                  <tr>
                    <th className="text-left p-2">Priority</th>
                    <th className="text-left p-2">Source</th>
                    <th className="text-left p-2">Target</th>
                    <th className="text-left p-2">Shared</th>
                    <th className="text-left p-2">Target Pos</th>
                    <th className="text-left p-2">Reasoning</th>
                  </tr>
                </thead>
                <tbody>
                  {result.entries.slice(0, 50).map((entry, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                            priorityColors[entry.priority] || ""
                          }`}
                        >
                          {entry.priority.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-2 truncate max-w-[200px]">
                        {new URL(entry.source_url).pathname}
                      </td>
                      <td className="p-2 truncate max-w-[200px]">
                        {new URL(entry.target_url).pathname}
                      </td>
                      <td className="p-2">{entry.shared_query_count}</td>
                      <td className="p-2">{entry.target_position.toFixed(1)}</td>
                      <td className="p-2 text-muted-foreground truncate max-w-[250px]">
                        {entry.reasoning}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
