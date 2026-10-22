export const TRUTH_COLOR = "#1f2937";
export const GPS_COLOR = "#2563eb";
const ESTIMATOR_COLORS: Record<string, string> = { baseline: "#ea580c" };
export const estimatorColor = (name: string) => ESTIMATOR_COLORS[name] ?? "#7c3aed";
