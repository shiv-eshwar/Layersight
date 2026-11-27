import Link from "next/link";

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
    <main className="w-full px-5 py-6 lg:px-8" data-testid="screen-ready">
      <p className="text-xs text-[#949aab]">
        <Link href="/" className="hover:text-white">Home</Link>
        <span className="px-1.5">/</span>
        <span className="text-[#d5d8e2]">{title}</span>
      </p>
      <h1 data-testid="screen-title" className="mt-3 text-[1.85rem] leading-none font-semibold tracking-[-0.035em]">{title}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#949aab]">{purpose}</p>
      <div className="mt-6">{children}</div>
    </main>
  );
}
