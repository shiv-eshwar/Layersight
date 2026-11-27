"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";

import { fetchStoredConfig } from "@/lib/flagship/api";
import { useFlagship } from "@/lib/flagship/store";

import "./flagship.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
});

function HydrateConfigs() {
  const hydrate = useFlagship((state) => state.hydrate);
  useEffect(() => {
    let cancelled = false;
    void Promise.all([fetchStoredConfig("untrained"), fetchStoredConfig("trained")])
      .then(([untrained, trained]) => {
        if (!cancelled) hydrate(untrained, trained);
      })
      .catch(() => {
        // The screens report a missing dataset or a failed run themselves.
      });
    return () => {
      cancelled = true;
    };
  }, [hydrate]);
  return null;
}

export function FlagshipProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <HydrateConfigs />
      <div className="ls">{children}</div>
    </QueryClientProvider>
  );
}
