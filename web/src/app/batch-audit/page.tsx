// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { BatchFileUploader } from "@/components/batch-file-uploader";
import { BatchAuditSummary } from "@/components/batch-audit-summary";
import { batchAuditFiles } from "@/lib/api";
import type { BatchAuditResult } from "@/lib/types";

export default function BatchAuditPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [siteDomain, setSiteDomain] = useState("");
  const [result, setResult] = useState<BatchAuditResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAudit() {
    if (files.length === 0) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await batchAuditFiles(files, siteDomain || undefined);
      setResult(res);
    } catch (e) {
      toast.error(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 p-6">
      <Card>
        <CardContent className="space-y-4 p-6">
          <BatchFileUploader onFiles={setFiles} />
          <div className="space-y-1.5">
            <Label>Site Domain (optional)</Label>
            <Input
              placeholder="www.example.com"
              value={siteDomain}
              onChange={(e) => setSiteDomain(e.target.value)}
            />
          </div>
          <Button
            onClick={handleAudit}
            disabled={files.length === 0 || loading}
          >
            {loading ? "Auditing..." : "Audit All"}
          </Button>
        </CardContent>
      </Card>

      {result && <BatchAuditSummary result={result} />}
    </div>
  );
}
