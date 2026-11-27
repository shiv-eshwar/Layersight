"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { apiUrl } from "@/lib/assumptions";

type Statement = { title: string; body: string };

const fallback: Statement[] = [
  {
    title: "Layer independence",
    body: "Given an email, each layer is assumed to stop the attack on its own. These are model estimates, not measurements.",
  },
  {
    title: "User catch rate",
    body: "Training sets a base rate: none 30%, basic 55%, advanced 75%.",
  },
];

export function AssumptionsSheet() {
  const [statements, setStatements] = useState<Statement[]>(fallback);
  const [source, setSource] = useState("The engine did not respond. These are the documented defaults.");

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiUrl}/api/v1/meta`)
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json() as Promise<{
          engine_version: string;
          assumptions?: { statements?: Statement[] };
        }>;
      })
      .then((meta) => {
        if (cancelled) return;
        const next = meta.assumptions?.statements;
        if (next && next.length > 0) {
          setStatements(next);
          setSource(`Read from the engine, version ${meta.engine_version}.`);
        }
      })
      .catch(() => {
        if (!cancelled) setSource("The engine did not respond. These are the documented defaults.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Sheet>
      <SheetTrigger render={<Button variant="outline" size="sm" />}>Assumptions</SheetTrigger>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Modeled estimates</SheetTitle>
          <SheetDescription>
            Pass-through rates are estimates from these assumptions, not measurements of a live network.
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-4 px-4 pb-6 text-sm leading-6">
          <p className="text-muted-foreground">{source}</p>
          {statements.map((item) => (
            <section key={item.title}>
              <h3 className="font-medium">{item.title}</h3>
              <p className="text-muted-foreground">{item.body}</p>
            </section>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}
