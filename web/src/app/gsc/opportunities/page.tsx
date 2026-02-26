// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
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
import { getOpportunities } from "@/lib/api";
import type { Opportunity } from "@/lib/types";

const priorityColor: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  high: "destructive",
  quick_win: "default",
  medium: "secondary",
  low: "outline",
};

export default function OpportunitiesPage() {
  const [siteUrl, setSiteUrl] = useState("");
  const [days, setDays] = useState(28);
  const [minImpressions, setMinImpressions] = useState(100);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleFetch() {
    if (!siteUrl) return;
    setLoading(true);
    try {
      const res = await getOpportunities(siteUrl, days, minImpressions);
      setOpportunities(res);
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
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <Label>GSC Site URL</Label>
              <Input
                placeholder="sc-domain:example.com"
                value={siteUrl}
                onChange={(e) => setSiteUrl(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Days</Label>
              <Input
                type="number"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Min Impressions</Label>
              <Input
                type="number"
                value={minImpressions}
                onChange={(e) => setMinImpressions(Number(e.target.value))}
              />
            </div>
          </div>
          <Button onClick={handleFetch} disabled={!siteUrl || loading}>
            {loading ? "Loading..." : "Fetch Opportunities"}
          </Button>
        </CardContent>
      </Card>

      {opportunities.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="mb-3 text-sm text-muted-foreground">
              {opportunities.length} opportunities found
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>URL</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right">Impressions</TableHead>
                  <TableHead className="text-right">Clicks</TableHead>
                  <TableHead className="text-right">Position</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {opportunities.map((o, i) => (
                  <TableRow key={i}>
                    <TableCell className="max-w-xs truncate text-xs">
                      {o.url}
                    </TableCell>
                    <TableCell>
                      <Badge variant={priorityColor[o.priority]}>
                        {o.priority}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {o.opportunity_score.toFixed(3)}
                    </TableCell>
                    <TableCell className="text-right">
                      {o.impressions.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {o.clicks.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {o.position.toFixed(1)}
                    </TableCell>
                    <TableCell className="max-w-sm text-xs">
                      {o.reason}
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
