export const TRUTH_COLOR = "#1f2937";
export const GPS_COLOR = "#2563eb";
export const ROUTE_COLOR = "#059669";
const ESTIMATOR_COLORS: Record<string, string> = { baseline: "#ea580c", "map filter": "#7c3aed" };
export const estimatorColor = (name: string) => ESTIMATOR_COLORS[name] ?? "#0891b2";

// The estimator's colour, see-through, for its uncertainty band
export function bandColor(name: string) {
  const hex = estimatorColor(name);
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, 0.18)`;
}

// GPS fixes by portal phase: blue when trustworthy, warm colours when not
export const GPS_PHASE_COLORS: Record<string, string> = {
  open: "#2563eb", fade: "#60a5fa", converging: "#60a5fa",
  multipath: "#dc2626", coast: "#a21caf", exit_bias: "#dc2626",
};
export const AXIS_COLORS = ["#dc2626", "#16a34a", "#2563eb"]; // phone x, y, z
