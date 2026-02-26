"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CandidatePage } from "@/lib/types";

type SortKey = "url" | "opportunity_score" | "impressions" | "avg_position";

export function CandidateTable({
  candidates,
}: {
  candidates: CandidatePage[];
}) {
  const [sortKey, setSortKey] = useState<SortKey>("opportunity_score");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = [...candidates].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    if (typeof av === "string" && typeof bv === "string")
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortAsc
      ? (av as number) - (bv as number)
      : (bv as number) - (av as number);
  });

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="cursor-pointer" onClick={() => toggleSort("url")}>
            URL
          </TableHead>
          <TableHead>Title</TableHead>
          <TableHead
            className="cursor-pointer text-right"
            onClick={() => toggleSort("opportunity_score")}
          >
            Opp. Score
          </TableHead>
          <TableHead
            className="cursor-pointer text-right"
            onClick={() => toggleSort("impressions")}
          >
            Impressions
          </TableHead>
          <TableHead
            className="cursor-pointer text-right"
            onClick={() => toggleSort("avg_position")}
          >
            Position
          </TableHead>
          <TableHead>Top Queries</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((c, i) => (
          <TableRow key={i}>
            <TableCell className="max-w-xs truncate text-xs">
              {c.url}
            </TableCell>
            <TableCell className="max-w-[200px] truncate text-sm">
              {c.title || c.h1 || "—"}
            </TableCell>
            <TableCell className="text-right">
              <Badge
                variant={
                  c.opportunity_score > 0.5
                    ? "default"
                    : c.opportunity_score > 0.2
                      ? "secondary"
                      : "outline"
                }
              >
                {c.opportunity_score.toFixed(3)}
              </Badge>
            </TableCell>
            <TableCell className="text-right">
              {c.impressions > 0 ? c.impressions.toLocaleString() : "—"}
            </TableCell>
            <TableCell className="text-right">
              {c.avg_position > 0 ? c.avg_position.toFixed(1) : "—"}
            </TableCell>
            <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">
              {c.top_queries.slice(0, 3).join(", ") || "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
