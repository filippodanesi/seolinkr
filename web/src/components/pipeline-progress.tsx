// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";

interface PipelineProgressProps {
  logs: string[];
  isRunning: boolean;
}

export function PipelineProgress({ logs, isRunning }: PipelineProgressProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0 && !isRunning) return null;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-2 flex items-center gap-2">
          <h3 className="text-sm font-medium">Pipeline Progress</h3>
          {isRunning && (
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-green-500" />
          )}
        </div>
        <div className="max-h-64 overflow-y-auto rounded bg-muted p-3 font-mono text-xs">
          {logs.map((log, i) => (
            <div key={i} className="py-0.5">
              {log}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </CardContent>
    </Card>
  );
}
