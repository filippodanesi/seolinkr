// Copyright (c) 2025-2026 Filippo Danesi. All rights reserved.
"use client";

import { useCallback, useState } from "react";
import { cn } from "@/lib/utils";

interface FileUploaderProps {
  accept?: string;
  onFile: (file: File) => void;
  className?: string;
}

export function FileUploader({
  accept = ".md,.markdown,.docx,.xlsx",
  onFile,
  className,
}: FileUploaderProps) {
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        setFileName(file.name);
        onFile(file);
      }
    },
    [onFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setFileName(file.name);
        onFile(file);
      }
    },
    [onFile]
  );

  return (
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
          : "border-muted-foreground/25 hover:border-primary/50",
        className
      )}
    >
      <p className="text-sm font-medium">
        {fileName ?? "Drop file here or click to browse"}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Supports .md, .docx, .xlsx
      </p>
      <input
        type="file"
        accept={accept}
        onChange={handleChange}
        className="hidden"
      />
    </label>
  );
}
