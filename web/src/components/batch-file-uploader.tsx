// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useCallback, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface BatchFileUploaderProps {
  accept?: string;
  onFiles: (files: File[]) => void;
  className?: string;
}

export function BatchFileUploader({
  accept = ".md,.markdown,.docx,.xlsx",
  onFiles,
  className,
}: BatchFileUploaderProps) {
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      const arr = Array.from(newFiles);
      const merged = [...files];
      for (const f of arr) {
        if (!merged.some((e) => e.name === f.name && e.size === f.size)) {
          merged.push(f);
        }
      }
      setFiles(merged);
      onFiles(merged);
    },
    [files, onFiles]
  );

  const removeFile = useCallback(
    (index: number) => {
      const next = files.filter((_, i) => i !== index);
      setFiles(next);
      onFiles(next);
    },
    [files, onFiles]
  );

  const clearAll = useCallback(() => {
    setFiles([]);
    onFiles([]);
  }, [onFiles]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.length) addFiles(e.target.files);
      e.target.value = "";
    },
    [addFiles]
  );

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return (
    <div className={className}>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50"
        )}
      >
        <p className="text-sm font-medium">
          Drop files here or click to browse
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Supports .md, .docx, .xlsx &mdash; multiple files allowed
        </p>
        <input
          type="file"
          accept={accept}
          multiple
          onChange={handleChange}
          className="hidden"
        />
      </label>

      {files.length > 0 && (
        <div className="mt-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {files.length} file{files.length !== 1 ? "s" : ""} selected
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs"
              onClick={clearAll}
            >
              Clear all
            </Button>
          </div>
          {files.map((f, i) => (
            <div
              key={`${f.name}-${f.size}`}
              className="flex items-center justify-between rounded bg-muted px-3 py-1.5 text-sm"
            >
              <span className="truncate">{f.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {formatSize(f.size)}
                </span>
                <button
                  onClick={() => removeFile(i)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
