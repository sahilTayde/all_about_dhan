const LINKS = [
  { href: "/desk", label: "Desk", hint: "Signals & book" },
  { href: "/pm", label: "Founder", hint: "Money & models" },
];

export function AppNav({ current }) {
  const path = current || (typeof window !== "undefined" ? window.location.pathname : "/");
  return (
    <nav className="app-nav" aria-label="Dashboards">
      {LINKS.map((l) => {
        const active = path === l.href || path.startsWith(`${l.href}/`);
        return (
          <a key={l.href} href={l.href} className={active ? "app-nav__link is-active" : "app-nav__link"}>
            <strong>{l.label}</strong>
            <span>{l.hint}</span>
          </a>
        );
      })}
    </nav>
  );
}
