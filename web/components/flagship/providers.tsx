"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "./flagship.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false, staleTime: 30_000 },
  },
});

export function FlagshipProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="ls">{children}</div>
    </QueryClientProvider>
  );
}
