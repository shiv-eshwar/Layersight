"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

/** The dataset in the URL, or the newest stored set once the API answers. */
export function useWorkspaceDataset(): string | null {
  const params = useSearchParams();
  const requested = params.get("dataset");
  const search = params.toString();
  const router = useRouter();
  const pathname = usePathname();
  const [fallback, setFallback] = useState<string | null>(requested);

  useEffect(() => {
    if (requested) {
      setFallback(requested);
      return;
    }
    let cancelled = false;
    void api<{ id: string }[]>("/api/v1/datasets")
      .then((rows) => {
        if (cancelled) return;
        const id = rows[0]?.id;
        if (!id) {
          setFallback("dev");
          return;
        }
        const query = new URLSearchParams(search);
        query.set("dataset", id);
        router.replace(`${pathname}?${query.toString()}`);
      })
      .catch(() => {
        if (!cancelled) setFallback("dev");
      });
    return () => {
      cancelled = true;
    };
  }, [requested, pathname, router, search]);

  return requested || fallback;
}
