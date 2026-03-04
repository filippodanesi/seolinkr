// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useRef, useState, useCallback } from "react";
import { toast } from "sonner";
import { OctagonX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BatchFileUploader } from "@/components/batch-file-uploader";
import { GscSiteSelector } from "@/components/gsc-site-selector";
import { BatchProgress, type FileStatus } from "@/components/batch-progress";
import { BatchSummary } from "@/components/batch-summary";
import { SitemapSelector } from "@/components/sitemap-selector";
import { runBatchPipeline } from "@/lib/api";
import type { BatchResult, BatchSSEEvent, LinkingResult } from "@/lib/types";

export default function BatchProcessPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [sitemap, setSitemap] = useState("");
  const [maxLinks, setMaxLinks] = useState(10);
  const [topN, setTopN] = useState(40);
  const [gscSite, setGscSite] = useState("");
  const [enableRewrite, setEnableRewrite] = useState(false);
  const [generateHtml, setGenerateHtml] = useState(false);

  const [sharedLogs, setSharedLogs] = useState<string[]>([]);
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([]);
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Collect per-file results for the summary (with output_base64 etc.)
  const fileResultsRef = useRef<Map<string, LinkingResult>>(new Map());

  const handleProcess = useCallback(async () => {
    if (files.length === 0 || !sitemap) return;
    setRunning(true);
    setSharedLogs([]);
    setBatchResult(null);
    fileResultsRef.current.clear();

    // Initialize file statuses
    setFileStatuses(
      files.map((f) => ({
        filename: f.name,
        status: "pending" as const,
        logs: [],
      }))
    );

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runBatchPipeline(
        files,
        sitemap,
        {
          maxLinks,
          topN,
          gscSite: gscSite || undefined,
          enableRewrite,
          generateHtml,
          signal: controller.signal,
        },
        (event: BatchSSEEvent) => {
          switch (event.type) {
            case "log":
              setSharedLogs((prev) => [...prev, event.message]);
              break;
            case "file_start":
              setCurrentFileIndex(event.file_index);
              setFileStatuses((prev) =>
                prev.map((f, i) =>
                  i === event.file_index
                    ? { ...f, status: "processing" as const }
                    : f
                )
              );
              break;
            case "file_log":
              setFileStatuses((prev) =>
                prev.map((f, i) =>
                  i === event.file_index
                    ? { ...f, logs: [...f.logs, event.message] }
                    : f
                )
              );
              break;
            case "file_done":
              fileResultsRef.current.set(event.filename, event.result);
              setFileStatuses((prev) =>
                prev.map((f, i) =>
                  i === event.file_index
                    ? {
                        ...f,
                        status: "success" as const,
                        linksInserted: event.result.insertions?.length ?? 0,
                      }
                    : f
                )
              );
              break;
            case "file_error":
              setFileStatuses((prev) =>
                prev.map((f, i) =>
                  i === event.file_index
                    ? { ...f, status: "error" as const, error: event.error }
                    : f
                )
              );
              break;
            case "batch_summary": {
              // Merge per-file results with full data (including output_base64)
              const summary = event.data;
              for (const fr of summary.file_results) {
                const full = fileResultsRef.current.get(fr.filename);
                if (full && fr.status === "success") {
                  fr.result = full;
                }
              }
              setBatchResult(summary);
              break;
            }
            case "error":
              toast.error(event.message);
              break;
          }
        },
        () => setRunning(false)
      );
    } catch (e) {
      if (controller.signal.aborted) {
        setSharedLogs((prev) => [
          ...prev,
          "\u274C Batch cancelled by user.",
        ]);
      } else {
        const msg = String(e);
        setSharedLogs((prev) => [...prev, `\u274C Error: ${msg}`]);
        toast.error(msg);
      }
      setRunning(false);
    } finally {
      abortRef.current = null;
    }
  }, [files, sitemap, maxLinks, topN, gscSite, enableRewrite, generateHtml]);

  function handleCancel() {
    abortRef.current?.abort();
  }

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardContent className="space-y-4 p-6">
          <BatchFileUploader onFiles={setFiles} />
          <div className="grid grid-cols-2 gap-4">
            <SitemapSelector value={sitemap} onChange={setSitemap} />
            <GscSiteSelector
              label="GSC Site (optional)"
              value={gscSite}
              onChange={setGscSite}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
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
          <div className="flex gap-2">
            <Button
              onClick={handleProcess}
              disabled={files.length === 0 || !sitemap || running}
            >
              {running ? "Processing..." : "Process All"}
            </Button>
            {running && (
              <Button variant="destructive" onClick={handleCancel}>
                <OctagonX className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <BatchProgress
        sharedLogs={sharedLogs}
        fileStatuses={fileStatuses}
        isRunning={running}
        currentFileIndex={currentFileIndex}
        totalFiles={files.length}
      />

      {batchResult && <BatchSummary result={batchResult} />}
    </div>
  );
}
