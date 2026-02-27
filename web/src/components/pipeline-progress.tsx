// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useRef, useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface PipelineProgressProps {
  logs: string[];
  isRunning: boolean;
}

export function PipelineProgress({ logs, isRunning }: PipelineProgressProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(true);
  const wasRunning = useRef(false);

  useEffect(() => {
    if (isRunning) {
      wasRunning.current = true;
      setOpen(true);
    } else if (wasRunning.current) {
      // Auto-collapse when pipeline finishes
      wasRunning.current = false;
      setOpen(false);
    }
  }, [isRunning]);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, open]);

  if (logs.length === 0 && !isRunning) return null;

  const hasError = logs.some((l) => l.startsWith("\u274C"));

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <button className="flex w-full items-center justify-between p-4 text-left">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium">Pipeline Logs</h3>
              {isRunning && (
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-green-500" />
              )}
              {!isRunning && hasError && (
                <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
              )}
              {!isRunning && !hasError && logs.length > 0 && (
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
              )}
              {!isRunning && logs.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {logs.length} entries
                </span>
              )}
            </div>
            <ChevronDown
              className={`h-4 w-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
            />
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="px-4 pb-4 pt-0">
            <div className="max-h-64 overflow-y-auto rounded bg-muted p-3 font-mono text-xs">
              {logs.map((log, i) => (
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
  );
}
