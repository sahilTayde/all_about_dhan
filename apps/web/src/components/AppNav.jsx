export const NAV_LINKS = [
  { href: "/desk", label: "Live" },
  { href: "/desk/signals", label: "Signals" },
  { href: "/desk/history", label: "Journal" },
  { href: "/desk/strategies", label: "Strategies" },
  { href: "/pm", label: "Money" },
  { href: "/ops", label: "Ops" },
  { href: "/", label: "Customer" },
];

/** Light nav for pages without the desk feed (customer page, 404). */
export function AppNav({ current }) {
  const path = current || (typeof window !== "undefined" ? window.location.pathname : "/");
  return (
    <header className="tb">
      <div className="tb__row">
        <a className="tb__brand" href="/desk">all_about_dhan<span>paper desk</span></a>
        <nav className="tb__nav" aria-label="Pages">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} className={path === l.href ? "is-on" : ""}>{l.label}</a>
          ))}
        </nav>
      </div>
    </header>
  );
}
