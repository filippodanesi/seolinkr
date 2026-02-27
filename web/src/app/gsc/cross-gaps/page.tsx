// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { GscSiteSelector } from "@/components/gsc-site-selector";
import { getCrossGaps } from "@/lib/api";
import type { CrossLinkOpportunity } from "@/lib/types";

export default function CrossGapsPage() {
  const [siteUrl, setSiteUrl] = useState("");
  const [urlPattern, setUrlPattern] = useState("/magazine/|/magazin/");
  const [gaps, setGaps] = useState<CrossLinkOpportunity[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleFetch() {
    if (!siteUrl) return;
    setLoading(true);
    try {
      const res = await getCrossGaps(siteUrl, urlPattern);
      setGaps(res);
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
          <div className="grid grid-cols-2 gap-4">
            <GscSiteSelector
              label="GSC Site URL"
              value={siteUrl}
              onChange={setSiteUrl}
            />
            <div className="space-y-1.5">
              <Label>URL Pattern</Label>
              <Input
                value={urlPattern}
                onChange={(e) => setUrlPattern(e.target.value)}
              />
            </div>
          </div>
          <Button onClick={handleFetch} disabled={!siteUrl || loading}>
            {loading ? "Loading..." : "Find Cross-Link Gaps"}
          </Button>
        </CardContent>
      </Card>

      {gaps.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="mb-3 text-sm text-muted-foreground">
              {gaps.length} cross-link opportunities found
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead className="text-right">Shared Queries</TableHead>
                  <TableHead className="text-right">Target Impressions</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead>Top Shared Queries</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {gaps.map((g, i) => (
                  <TableRow key={i}>
                    <TableCell className="max-w-[180px] truncate text-xs">
                      {g.source_url}
                    </TableCell>
                    <TableCell className="max-w-[180px] truncate text-xs">
                      {g.target_url}
                    </TableCell>
                    <TableCell className="text-right">
                      {g.shared_query_count}
                    </TableCell>
                    <TableCell className="text-right">
                      {g.target_impressions.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {g.relevance_score.toFixed(3)}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">
                      {g.shared_queries.slice(0, 3).join(", ")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
