export const TRUTH_COLOR = "#1f2937";
export const GPS_COLOR = "#2563eb";
const ESTIMATOR_COLORS: Record<string, string> = { baseline: "#ea580c" };
export const estimatorColor = (name: string) => ESTIMATOR_COLORS[name] ?? "#7c3aed";

// GPS fixes by portal phase: blue when trustworthy, warm colours when not
export const GPS_PHASE_COLORS: Record<string, string> = {
  open: "#2563eb", fade: "#60a5fa", converging: "#60a5fa",
  multipath: "#dc2626", coast: "#a21caf", exit_bias: "#dc2626",
};
export const AXIS_COLORS = ["#dc2626", "#16a34a", "#2563eb"]; // phone x, y, z
