import type { Run } from "./api";

type Props = { run: Run };

// The real tunnel this scenario's road is simplified from, small, on OpenStreetMap.
// The simulated road keeps its length, curves, grades and exits; it is not traced from this map.
export default function RealMap({ run }: Props) {
  const { name, west, south, east, north } = run.scenario.road.based_on;
  const bbox = [west, south, east, north].join(",");
  const marker = `${(south + north) / 2},${(west + east) / 2}`;
  const embed = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${marker}`;
  const full = `https://www.openstreetmap.org/?minlon=${west}&minlat=${south}&maxlon=${east}&maxlat=${north}`;
  return (
    <figure className="real-map">
      <iframe title={name} src={embed} loading="lazy" />
      <figcaption>Based on <b>{name}</b> · <a href={full} target="_blank" rel="noreferrer">open map</a></figcaption>
    </figure>
  );
}
