// PROTOTYPE (replay layout, throwaway): three layouts of the replay page on the same route,
// switched with ?variant=0|A|B|C and the floating bar. 0 is today's page, for comparison.
// The variants share the data (one run + its metrics) and the existing drawing components;
// only the arrangement differs.
import { useEffect, useState } from "react";
import App from "../App";
import { useReplay } from "./shared";
import VariantA, { name as nameA } from "./VariantA";
import VariantB, { name as nameB } from "./VariantB";
import VariantC, { name as nameC } from "./VariantC";
import "./prototype.css";

const VARIANTS = [
  { key: "0", name: "today's page" },
  { key: "A", name: nameA },
  { key: "B", name: nameB },
  { key: "C", name: nameC },
];

export default function ReplayPrototype() {
  const [variant, setVariant] = useState(() => new URLSearchParams(location.search).get("variant") ?? "A");
  const choose = (key: string) => {
    const params = new URLSearchParams(location.search);
    params.set("variant", key);
    history.replaceState(null, "", `?${params}`);
    setVariant(key);
  };
  return (
    <>
      {variant === "0" ? <App /> : <Variants variant={variant} />}
      <PrototypeSwitcher current={variant} choose={choose} />
    </>
  );
}

function Variants({ variant }: { variant: string }) {
  const r = useReplay();
  if (!r.run || !r.scenario) {
    return <main>{r.error ? <p className="error">{r.error}</p> : <p className="computing"><span className="spinner" /> Computing run…</p>}</main>;
  }
  if (variant === "B") return <VariantB r={r} />;
  if (variant === "C") return <VariantC r={r} />;
  return <VariantA r={r} />;
}

function PrototypeSwitcher({ current, choose }: { current: string; choose: (key: string) => void }) {
  const i = Math.max(0, VARIANTS.findIndex((v) => v.key === current));
  const step = (d: number) => choose(VARIANTS[(i + d + VARIANTS.length) % VARIANTS.length].key);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)) return;
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  return (
    <div className="proto-switcher">
      <button onClick={() => step(-1)}>←</button>
      <span>PROTOTYPE · {VARIANTS[i].key} ({VARIANTS[i].name})</span>
      <button onClick={() => step(1)}>→</button>
    </div>
  );
}
