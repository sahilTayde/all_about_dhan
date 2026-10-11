export function Skeleton({ lines = 3, testid = "skeleton" }) {
  return (
    <div className="skeleton" data-testid={testid} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <i key={i} style={{ width: `${88 - i * 12}%` }} />
      ))}
    </div>
  );
}
