// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
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

function handleDownload(base64: string, filename: string) {
  const byteChars = atob(base64);
  const byteNumbers = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    byteNumbers[i] = byteChars.charCodeAt(i);
  }
  const blob = new Blob([byteNumbers]);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function LinkReport({ result }: { result: LinkingResult }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">
          Inserted Links
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            ({result.insertions.length})
          </span>
        </CardTitle>
        {result.output_base64 && result.output_filename && (
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              handleDownload(result.output_base64!, result.output_filename!)
            }
          >
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        )}
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
  );
}
