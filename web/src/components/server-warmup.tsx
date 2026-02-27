// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useEffect, useState } from "react";
import { healthCheck } from "@/lib/api";
import { Loader2 } from "lucide-react";

const POLL_INTERVAL = 3000;
const MAX_ATTEMPTS = 30; // ~90s max wait

export function ServerWarmup({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    async function poll() {
      const ok = await healthCheck();
      if (cancelled) return;
      if (ok) {
        setReady(true);
        return;
      }
      attempts += 1;
      if (attempts < MAX_ATTEMPTS) {
        setTimeout(poll, POLL_INTERVAL);
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  if (ready) return <>{children}</>;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <div>
          <p className="text-lg font-medium">Starting server...</p>
          <p className="text-sm text-muted-foreground">
            The backend is waking up. This usually takes 30-50 seconds.
          </p>
        </div>
      </div>
    </div>
  );
}
