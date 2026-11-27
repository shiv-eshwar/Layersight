"use client";

import { useState } from "react";

type ListedFile = {
  name: string;
  size: number;
};

export function TriageInbox() {
  const [files, setFiles] = useState<ListedFile[]>([]);

  function take(list: FileList | null) {
    if (!list || list.length === 0) return;
    setFiles(Array.from(list, (file) => ({ name: file.name, size: file.size })));
  }

  return (
    <div className="flex flex-col gap-6">
      <label
        data-testid="triage-dropzone"
        className="block cursor-pointer border border-dashed border-border bg-card px-6 py-10 text-center focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          take(event.dataTransfer.files);
        }}
      >
        <input
          type="file"
          multiple
          accept=".eml,.txt,.zip,message/rfc822,text/plain"
          className="sr-only"
          onChange={(event) => take(event.target.files)}
        />
        <span className="block text-sm font-medium">Drop email files here, or choose them</span>
        <span className="mt-1 block text-sm text-muted-foreground">
          .eml, .txt, or a .zip. Attachment contents are never read.
        </span>
      </label>
      {files.length > 0 ? (
        <div className="overflow-x-auto border border-border">
          <table className="w-full text-left text-sm">
            <caption className="border-b border-border px-4 py-3 text-left text-muted-foreground">
              {files.length} {files.length === 1 ? "file" : "files"} in this tab. Nothing has been
              uploaded or classified.
            </caption>
            <thead className="text-muted-foreground">
              <tr className="border-b border-border">
                <th className="px-4 py-2 font-medium">File</th>
                <th className="px-4 py-2 font-medium">Prediction</th>
                <th className="px-4 py-2 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.name} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 font-mono text-[13px]">{file.name}</td>
                  <td className="px-4 py-2 text-muted-foreground">—</td>
                  <td className="px-4 py-2 font-mono text-muted-foreground">—</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
