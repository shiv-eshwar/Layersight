export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="border border-border border-l-2 border-l-intelligence bg-card px-6 py-8">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">{children}</div>
      {action ? <div className="mt-5">{action}</div> : null}
    </section>
  );
}
