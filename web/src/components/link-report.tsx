// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { LinkingResult } from "@/lib/types";

export function LinkReport({ result }: { result: LinkingResult }) {
  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold">{result.insertions.length}</p>
            <p className="text-xs text-muted-foreground">Links Inserted</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold">{result.candidate_pages_count}</p>
            <p className="text-xs text-muted-foreground">Candidates</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold">{result.total_sitemap_pages}</p>
            <p className="text-xs text-muted-foreground">Sitemap Pages</p>
          </CardContent>
        </Card>
      </div>

      {/* SEO metadata */}
      {result.seo_title && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">SEO Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              <span className="font-medium">Title:</span> {result.seo_title}
            </p>
            <p>
              <span className="font-medium">Description:</span>{" "}
              {result.seo_meta_description}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Insertions table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Inserted Links</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Anchor Text</TableHead>
                <TableHead>Target URL</TableHead>
                <TableHead>Reasoning</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.insertions.map((ins, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">
                    {ins.anchor_text}
                  </TableCell>
                  <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                    {ins.target_url}
                  </TableCell>
                  <TableCell className="max-w-sm text-xs">
                    {ins.reasoning}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Output preview */}
      {result.output_content && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Output Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto rounded bg-muted p-3 text-xs">
              {result.output_content}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
