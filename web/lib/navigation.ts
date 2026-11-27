export const navigation = [
  { href: "/", label: "Command Center" },
  { href: "/triage", label: "Triage" },
  { href: "/intelligence", label: "Intelligence" },
  { href: "/defense", label: "Defense" },
  { href: "/simulator", label: "Simulator" },
  { href: "/compare", label: "Compare" },
  { href: "/academy", label: "Academy" },
  { href: "/reports", label: "Reports" },
] as const;

export function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
