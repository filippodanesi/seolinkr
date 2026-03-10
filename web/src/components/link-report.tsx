// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { Download, Monitor, Smartphone } from "lucide-react";
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
import { downloadBase64File } from "@/lib/download";
import type { LinkingResult } from "@/lib/types";

export function LinkReport({ result }: { result: LinkingResult }) {
  return (
    <div className="space-y-4">
      {/* SEO Metadata (when generated) */}
      {result.seo_title && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">SEO Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5 text-sm">
            <div>
              <span className="text-muted-foreground">Title: </span>
              {result.seo_title}
            </div>
            <div>
              <span className="text-muted-foreground">Meta Description: </span>
              {result.seo_meta_description}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Inserted Links */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-base">
            Inserted Links
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({result.insertions.length})
            </span>
          </CardTitle>
          <div className="flex gap-2">
            {result.output_base64 && result.output_filename && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  downloadBase64File(result.output_base64!, result.output_filename!)
                }
              >
                <Download className="mr-2 h-4 w-4" />
                Download
              </Button>
            )}
            {result.desktop_txt_base64 && result.desktop_txt_filename && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  downloadBase64File(
                    result.desktop_txt_base64!,
                    result.desktop_txt_filename!
                  )
                }
              >
                <Monitor className="mr-2 h-4 w-4" />
                Desktop TXT
              </Button>
            )}
            {result.mobile_txt_base64 && result.mobile_txt_filename && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  downloadBase64File(
                    result.mobile_txt_base64!,
                    result.mobile_txt_filename!
                  )
                }
              >
                <Smartphone className="mr-2 h-4 w-4" />
                Mobile TXT
              </Button>
            )}
          </div>
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
                  <TableCell>{ins.anchor_text}</TableCell>
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
    </div>
  );
}
