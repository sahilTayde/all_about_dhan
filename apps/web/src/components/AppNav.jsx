export const NAV_LINKS = [
  { href: "/", label: "Signal" },
  { href: "/desk", label: "Live trade" },
  { href: "/desk/history", label: "History" },
  { href: "/desk/strategies", label: "Strategies" },
  { href: "/pm", label: "Money" },
  { href: "/ops", label: "Ops" },
];

function isActive(path, href) {
  if (href === "/") return path === "/" || path === "" || path.startsWith("/customer");
  if (href === "/desk") return path === "/desk" || path === "/desk/";
  return path === href || path.startsWith(`${href}/`);
}

/** One shared nav for every page. `light` is an optional status light {tone,text}. */
export function AppNav({ current, light }) {
  const path = current || (typeof window !== "undefined" ? window.location.pathname : "/");
  return (
    <nav className="app-nav app-nav--flat" aria-label="Pages">
      <span className="app-nav__brand">all_about_dhan</span>
      {NAV_LINKS.map((l) => (
        <a key={l.href} href={l.href} className={isActive(path, l.href) ? "app-nav__link is-active" : "app-nav__link"} aria-current={isActive(path, l.href) ? "page" : undefined}>
          {l.label}
        </a>
      ))}
      {light ? (
        <span className={`status-light status-light--${light.tone}`} data-testid="status-light" title={light.text}>
          <i aria-hidden="true" /> {light.text}
        </span>
      ) : null}
    </nav>
  );
}
