// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { OctagonX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileUploader } from "@/components/file-uploader";
import { GscSiteSelector } from "@/components/gsc-site-selector";
import { PipelineProgress } from "@/components/pipeline-progress";
import { SitemapSelector } from "@/components/sitemap-selector";
import { runPLPPipeline } from "@/lib/api";
import type { PLPBatchResult, PLPSSEEvent } from "@/lib/types";

export default function ProcessPLPsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sitemap, setSitemap] = useState("");
  const [maxLinks, setMaxLinks] = useState(5);
  const [topN, setTopN] = useState(25);
  const [gscSite, setGscSite] = useState("");
  const [urlCol, setUrlCol] = useState("");
  const [contentCol, setContentCol] = useState("");
  const [keywordCol, setKeywordCol] = useState("");

  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<PLPBatchResult | null>(null);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function handleProcess() {
    if (!file || !sitemap) return;
    setRunning(true);
    setLogs([]);
    setResult(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runPLPPipeline(
        file,
        sitemap,
        {
          maxLinks,
          topN,
          gscSite: gscSite || undefined,
          urlCol: urlCol || undefined,
          contentCol: contentCol || undefined,
          keywordCol: keywordCol || undefined,
          signal: controller.signal,
        },
        (event: PLPSSEEvent) => {
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

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardContent className="space-y-4 p-6">
          <div>
            <h2 className="text-lg font-semibold mb-1">Process PLPs</h2>
            <p className="text-sm text-muted-foreground">
              Inject internal links into PLP SEO text blocks. Upload an XLSX
              with URL and HTML content columns.
            </p>
          </div>

          <FileUploader onFile={setFile} accept=".xlsx" />

          <div className="grid grid-cols-2 gap-4">
            <SitemapSelector value={sitemap} onChange={setSitemap} />
            <GscSiteSelector
              label="GSC Site (optional)"
              value={gscSite}
              onChange={setGscSite}
            />
          </div>

          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-1.5">
              <Label>URL Column</Label>
              <Input
                placeholder="Auto"
                value={urlCol}
                onChange={(e) => setUrlCol(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Content Column</Label>
              <Input
                placeholder="Auto (e.g. U)"
                value={contentCol}
                onChange={(e) => setContentCol(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Keyword Column</Label>
              <Input
                placeholder="Auto (e.g. M)"
                value={keywordCol}
                onChange={(e) => setKeywordCol(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Max Links/PLP</Label>
              <Input
                type="number"
                value={maxLinks}
                onChange={(e) => setMaxLinks(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleProcess}
              disabled={!file || !sitemap || running}
            >
              {running ? "Processing..." : "Process PLPs"}
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
            <h3 className="font-semibold">Results</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">PLPs processed:</span>{" "}
                {result.succeeded}/{result.total_rows}
              </div>
              <div>
                <span className="text-muted-foreground">Links inserted:</span>{" "}
                {result.total_links_inserted}
              </div>
              <div>
                <span className="text-muted-foreground">Failed:</span>{" "}
                {result.failed}
              </div>
            </div>

            {result.row_results
              .filter((r) => r.insertions.length > 0)
              .map((r) => (
                <div key={r.row_index} className="text-xs border-t pt-2">
                  <div className="font-medium">{r.url}</div>
                  {r.insertions.map((ins, i) => (
                    <div key={i} className="text-muted-foreground ml-4">
                      [{ins.anchor_text}] → {ins.target_url}
                    </div>
                  ))}
                </div>
              ))}

            {result.output_base64 && (
              <Button variant="outline" onClick={handleDownload}>
                Download XLSX
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
