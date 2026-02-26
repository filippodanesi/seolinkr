"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileUploader } from "@/components/file-uploader";
import { AuditResults } from "@/components/audit-results";
import { auditFile } from "@/lib/api";
import type { AuditResult } from "@/lib/types";

export default function AuditPage() {
  const [file, setFile] = useState<File | null>(null);
  const [siteDomain, setSiteDomain] = useState("");
  const [result, setResult] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAudit() {
    if (!file) return;
    setLoading(true);
    try {
      const res = await auditFile(file, siteDomain || undefined);
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
          <FileUploader onFile={setFile} />
          <div className="space-y-1.5">
            <Label>Site Domain (optional)</Label>
            <Input
              placeholder="www.example.com"
              value={siteDomain}
              onChange={(e) => setSiteDomain(e.target.value)}
            />
          </div>
          <Button onClick={handleAudit} disabled={!file || loading}>
            {loading ? "Auditing..." : "Run Audit"}
          </Button>
        </CardContent>
      </Card>

      {result && <AuditResults result={result} />}
    </div>
  );
}
