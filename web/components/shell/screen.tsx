export function Screen({
  title,
  purpose,
  children,
}: {
  title: string;
  purpose: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-8" data-testid="screen-ready">
      <h1 className="text-[1.75rem] leading-9 font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{purpose}</p>
      <div className="mt-8">{children}</div>
    </main>
  );
}
