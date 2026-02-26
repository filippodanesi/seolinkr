"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AuditResult } from "@/lib/types";

const severityColor: Record<string, string> = {
  error: "destructive",
  warning: "secondary",
  info: "outline",
};

export function AuditResults({ result }: { result: AuditResult }) {
  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <SummaryCard label="Total Links" value={result.total_links} />
        <SummaryCard label="Category" value={result.category_links} />
        <SummaryCard label="Magazine" value={result.magazine_links} />
        <SummaryCard label="Product" value={result.product_links} />
        <SummaryCard label="External" value={result.external_links} />
      </div>

      {/* Issues */}
      {result.issues.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Issues ({result.issues.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {result.issues.map((issue, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-sm"
                >
                  <Badge
                    variant={
                      severityColor[issue.severity] as
                        | "destructive"
                        | "secondary"
                        | "outline"
                    }
                    className="mt-0.5 shrink-0"
                  >
                    {issue.severity}
                  </Badge>
                  <span>{issue.message}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Link inventory */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Link Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Anchor Text</TableHead>
                <TableHead>Target URL</TableHead>
                <TableHead>Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.links.map((link, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">
                    {link.anchor_text}
                  </TableCell>
                  <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                    {link.target_url}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{link.link_type}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="p-3 text-center">
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}
