import type { Run } from "./api";

type Props = { run: Run };

// The real tunnel this scenario's road is simplified from, on OpenStreetMap.
// The pin marks the middle of the area; tunnels show as dashed road casings.
// The simulated road is not drawn to the same scale or heading.
export default function RealMap({ run }: Props) {
  const { name, west, south, east, north } = run.scenario.road.based_on;
  const bbox = [west, south, east, north].join(",");
  const marker = `${(south + north) / 2},${(west + east) / 2}`;
  const embed = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${marker}`;
  const full = `https://www.openstreetmap.org/?minlon=${west}&minlat=${south}&maxlon=${east}&maxlat=${north}`;
  return (
    <div>
      <iframe className="real-map" title={name} src={embed} loading="lazy" />
      <p className="caption">
        {name}. The simulated road keeps its length, curves, grades and exits, simplified; it is not
        traced from this map. <a href={full} target="_blank" rel="noreferrer">Open in OpenStreetMap</a>
      </p>
    </div>
  );
}
