// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileUploader } from "@/components/file-uploader";
import { CandidateTable } from "@/components/candidate-table";
import { SitemapSelector } from "@/components/sitemap-selector";
import { getCandidates } from "@/lib/api";
import type { CandidatePage } from "@/lib/types";

export default function CandidatesPage() {
  const [file, setFile] = useState<File | null>(null);
  const [sitemap, setSitemap] = useState("");
  const [topN, setTopN] = useState(40);
  const [gscSite, setGscSite] = useState("");
  const [candidates, setCandidates] = useState<CandidatePage[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleFetch() {
    if (!file || !sitemap) return;
    setLoading(true);
    try {
      const res = await getCandidates(file, sitemap, topN, gscSite || undefined);
      setCandidates(res);
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
          <SitemapSelector value={sitemap} onChange={setSitemap} />
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Top N</Label>
              <Input
                type="number"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
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
          <Button onClick={handleFetch} disabled={!file || !sitemap || loading}>
            {loading ? "Fetching..." : "Get Candidates"}
          </Button>
        </CardContent>
      </Card>

      {candidates.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="mb-3 text-sm text-muted-foreground">
              {candidates.length} candidates found
            </p>
            <CandidateTable candidates={candidates} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
