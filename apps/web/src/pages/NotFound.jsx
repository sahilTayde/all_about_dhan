import { AppNav } from "../components/AppNav.jsx";
import "../desk/desk.css";
import "../desk/pro.css";

export function NotFound() {
  return (
    <div className="shell rd-shell" data-testid="not-found">
      <AppNav />
      <section className="card">
        <h1>Page not found</h1>
        <p className="muted">There is no page at <code>{window.location.pathname}</code>. Pick one from the bar above.</p>
      </section>
    </div>
  );
}
