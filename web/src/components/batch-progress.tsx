// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useRef, useEffect, useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  Circle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export interface FileStatus {
  filename: string;
  status: "pending" | "processing" | "success" | "error";
  linksInserted?: number;
  error?: string;
  logs: string[];
}

interface BatchProgressProps {
  sharedLogs: string[];
  fileStatuses: FileStatus[];
  isRunning: boolean;
  currentFileIndex: number;
  totalFiles: number;
}

export function BatchProgress({
  sharedLogs,
  fileStatuses,
  isRunning,
  currentFileIndex,
  totalFiles,
}: BatchProgressProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [logsOpen, setLogsOpen] = useState(true);
  const wasRunning = useRef(false);

  useEffect(() => {
    if (isRunning) {
      wasRunning.current = true;
      setLogsOpen(true);
    } else if (wasRunning.current) {
      wasRunning.current = false;
      setLogsOpen(false);
    }
  }, [isRunning]);

  useEffect(() => {
    if (logsOpen) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [sharedLogs, logsOpen]);

  if (sharedLogs.length === 0 && fileStatuses.length === 0 && !isRunning) {
    return null;
  }

  const done = fileStatuses.filter(
    (f) => f.status === "success" || f.status === "error"
  ).length;

  return (
    <div className="space-y-3">
      {/* Overall progress */}
      {isRunning && totalFiles > 0 && (
        <div className="flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>
            Processing file {Math.min(currentFileIndex + 1, totalFiles)} of{" "}
            {totalFiles}
          </span>
        </div>
      )}

      {/* Per-file status list */}
      {fileStatuses.length > 0 && (
        <Card>
          <CardContent className="p-4 space-y-1.5">
            {fileStatuses.map((f, i) => (
              <div
                key={f.filename}
                className="flex items-center gap-2 text-sm"
              >
                {f.status === "processing" && (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500 shrink-0" />
                )}
                {f.status === "success" && (
                  <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                )}
                {f.status === "error" && (
                  <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                )}
                {f.status === "pending" && (
                  <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <span className="truncate">{f.filename}</span>
                {f.status === "success" && f.linksInserted !== undefined && (
                  <span className="text-xs text-muted-foreground">
                    {f.linksInserted} links
                  </span>
                )}
                {f.status === "error" && f.error && (
                  <span className="text-xs text-red-500 truncate">
                    {f.error}
                  </span>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Shared logs (collapsible) */}
      {sharedLogs.length > 0 && (
        <Collapsible open={logsOpen} onOpenChange={setLogsOpen}>
          <Card>
            <CollapsibleTrigger asChild>
              <button className="flex w-full items-center justify-between p-4 text-left">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium">Pipeline Logs</h3>
                  {isRunning && (
                    <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-green-500" />
                  )}
                  {!isRunning && sharedLogs.length > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {sharedLogs.length} entries
                    </span>
                  )}
                </div>
                <ChevronDown
                  className={`h-4 w-4 text-muted-foreground transition-transform ${logsOpen ? "rotate-180" : ""}`}
                />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent className="px-4 pb-4 pt-0">
                <div className="max-h-64 overflow-y-auto rounded bg-muted p-3 font-mono text-xs">
                  {sharedLogs.map((log, i) => (
                    <div
                      key={i}
                      className={`py-0.5 ${log.startsWith("\u274C") ? "text-red-600 font-medium" : ""}`}
                    >
                      {log}
                    </div>
                  ))}
                  <div ref={bottomRef} />
                </div>
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}
    </div>
  );
}
