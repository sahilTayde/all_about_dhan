import { plainCode } from "./plainWords.js";

/** Visible words; engine code only in the tooltip. */
export function Plain({ value, fallback = "Waiting for live price", as: Tag = "span", className }) {
  const { text, code } = plainCode(value, fallback);
  return (
    <Tag className={className} title={code || undefined}>
      {text}
    </Tag>
  );
}
