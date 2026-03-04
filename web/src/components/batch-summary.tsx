// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useState } from "react";
import { ChevronDown, Download } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { LinkReport } from "@/components/link-report";
import { downloadBase64File } from "@/lib/download";
import type { BatchResult } from "@/lib/types";

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="p-3 text-center">
        <p className="text-2xl font-medium">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

function getDownloadableFiles(result: BatchResult) {
  return result.file_results.filter(
    (fr) =>
      fr.status === "success" &&
      fr.result?.output_base64 &&
      fr.result?.output_filename
  );
}

function handleDownloadAll(result: BatchResult) {
  const files = getDownloadableFiles(result);
  for (const fr of files) {
    downloadBase64File(fr.result!.output_base64!, fr.result!.output_filename!);
  }
}

export function BatchSummary({ result }: { result: BatchResult }) {
  const downloadable = getDownloadableFiles(result);

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="Total Files" value={result.total_files} />
        <SummaryCard label="Succeeded" value={result.succeeded} />
        <SummaryCard label="Failed" value={result.failed} />
        <SummaryCard label="Total Links" value={result.total_links_inserted} />
      </div>

      {/* Download All */}
      {downloadable.length > 0 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDownloadAll(result)}
          >
            <Download className="mr-2 h-4 w-4" />
            Download All ({downloadable.length})
          </Button>
        </div>
      )}

      {/* Per-file results */}
      {result.file_results.map((fr, i) => (
        <FileResultCard key={i} fr={fr} />
      ))}
    </div>
  );
}

function FileResultCard({
  fr,
}: {
  fr: BatchResult["file_results"][number];
}) {
  const [open, setOpen] = useState(false);
  const hasDownload = fr.result?.output_base64 && fr.result?.output_filename;

  if (fr.status === "error") {
    return (
      <Card className="border-red-200">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">{fr.filename}</CardTitle>
            <Badge variant="destructive">Error</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-600">{fr.error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!fr.result) return null;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center justify-between p-4 text-left">
            <div className="flex items-center gap-2">
              <h3 className="text-sm">{fr.filename}</h3>
              <Badge variant="outline">
                {fr.result.insertions.length} links
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {hasDownload && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    downloadBase64File(
                      fr.result!.output_base64!,
                      fr.result!.output_filename!
                    );
                  }}
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
              )}
              <ChevronDown
                className={`h-4 w-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
              />
            </div>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0">
            <LinkReport result={fr.result} />
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
