// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileUploader } from "@/components/file-uploader";
import { PipelineProgress } from "@/components/pipeline-progress";
import { LinkReport } from "@/components/link-report";
import { SitemapSelector } from "@/components/sitemap-selector";
import { runPipeline } from "@/lib/api";
import type { LinkingResult, SSEEvent } from "@/lib/types";

export default function ProcessPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sitemap, setSitemap] = useState("");
  const [maxLinks, setMaxLinks] = useState(10);
  const [topN, setTopN] = useState(40);
  const [currentUrl, setCurrentUrl] = useState("");
  const [gscSite, setGscSite] = useState("");
  const [enableRewrite, setEnableRewrite] = useState(false);
  const [generateHtml, setGenerateHtml] = useState(false);

  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<LinkingResult | null>(null);
  const [running, setRunning] = useState(false);

  async function handleProcess() {
    if (!file || !sitemap) return;
    setRunning(true);
    setLogs([]);
    setResult(null);

    try {
      await runPipeline(
        file,
        sitemap,
        {
          maxLinks,
          topN,
          currentUrl: currentUrl || undefined,
          gscSite: gscSite || undefined,
          enableRewrite,
          generateHtml,
        },
        (event: SSEEvent) => {
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
      toast.error(String(e));
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6 p-6">
      <Card>
        <CardContent className="space-y-4 p-6">
          <FileUploader onFile={setFile} />
          <SitemapSelector value={sitemap} onChange={setSitemap} />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="space-y-1.5">
              <Label>Max Links</Label>
              <Input
                type="number"
                value={maxLinks}
                onChange={(e) => setMaxLinks(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Top N</Label>
              <Input
                type="number"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Current URL (optional)</Label>
              <Input
                placeholder="https://..."
                value={currentUrl}
                onChange={(e) => setCurrentUrl(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>GSC Site (optional)</Label>
              <Input
                placeholder="sc-domain:example.com"
                value={gscSite}
                onChange={(e) => setGscSite(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={enableRewrite}
                onChange={(e) => setEnableRewrite(e.target.checked)}
              />
              Enable rewrite
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={generateHtml}
                onChange={(e) => setGenerateHtml(e.target.checked)}
              />
              Generate SEO metadata
            </label>
          </div>
          <Button
            onClick={handleProcess}
            disabled={!file || !sitemap || running}
          >
            {running ? "Processing..." : "Process Article"}
          </Button>
        </CardContent>
      </Card>

      <PipelineProgress logs={logs} isRunning={running} />

      {result && <LinkReport result={result} />}
    </div>
  );
}
