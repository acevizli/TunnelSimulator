import { useState } from "react";
import type { PieceChoices, Scenario } from "./api";

type Props = {
  scenario: Scenario; choices: PieceChoices; computing: boolean;
  run: (s: Scenario) => void; save: (s: Scenario) => Promise<void>;
};
type Obj = Record<string, unknown>;

const KINDS = ["road", "speed", "mounting"] as const; // pieces whose "kind" picks the model
const HIDDEN = ["kind", "description", "based_on"]; // fixed facts about a piece, not settings

// Every piece of the scenario as a form. Edits stay a draft until "Run this" or "Save as".
// The form is built from the scenario itself, so a new number in the core shows up here unchanged.
export default function ScenarioEditor({ scenario, choices, computing, run, save }: Props) {
  const [draft, setDraft] = useState<Obj>(scenario as unknown as Obj);
  const [version, setVersion] = useState(0); // bumped to reset the typed-in fields
  const [saved, setSaved] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [from, setFrom] = useState(scenario);
  if (from !== scenario) { setFrom(scenario); setDraft(scenario as unknown as Obj); setVersion((v) => v + 1); }

  const set = (path: string[], value: unknown) => { setDraft((d) => setIn(d, path, value) as Obj); setSaved(null); };
  const changed = JSON.stringify(draft) !== JSON.stringify(scenario);
  const road = draft.road as Obj;
  const route = draft.route as Obj;
  const exits = choices.exits[road.kind as string] ?? [];

  const switchKind = (piece: (typeof KINDS)[number], kind: string) => {
    set([piece], choices[piece][kind]);
    // a planned exit the new road doesn't have would be refused
    if (piece === "road" && !(choices.exits[kind] ?? []).includes(route.planned_exit as string)) {
      set(["route"], { ...route, planned_exit: null, missed_exit: false });
    }
    setVersion((v) => v + 1);
  };
  const doSave = () => {
    setSaveError(null);
    save(draft as unknown as Scenario).then(() => setSaved(draft.name as string)).catch((e) => setSaveError(String(e.message ?? e)));
  };

  return (
    <div className="editor" key={version}>
      <label className="wide">name <input defaultValue={draft.name as string} onChange={(e) => set(["name"], e.target.value)} /></label>
      <label className="wide">description <textarea rows={2} defaultValue={draft.description as string}
        onChange={(e) => set(["description"], e.target.value)} /></label>
      {Object.entries(draft).filter(([k]) => !["name", "description", "seed"].includes(k)).map(([key, value]) => (
        <fieldset key={key}>
          <legend>{key.replace("_", " ")}</legend>
          {(KINDS as readonly string[]).includes(key) && (
            <label>kind <select value={(value as Obj).kind as string}
              onChange={(e) => switchKind(key as (typeof KINDS)[number], e.target.value)}>
              {Object.keys(choices[key as (typeof KINDS)[number]]).map((k) => <option key={k}>{k}</option>)}
            </select></label>
          )}
          {key === "road" && <p className="hint">{(value as Obj).description as string}</p>}
          {key === "route" ? <>
            <label>planned exit <select value={(route.planned_exit as string) ?? ""}
              onChange={(e) => set(["route"], { ...route, planned_exit: e.target.value || null, missed_exit: e.target.value ? route.missed_exit : false })}>
              <option value="">(stay on the main road)</option>
              {exits.map((x) => <option key={x}>{x}</option>)}
            </select></label>
            <label className="check"><input type="checkbox" checked={!!route.missed_exit} disabled={!route.planned_exit}
              onChange={(e) => set(["route", "missed_exit"], e.target.checked)} /> the driver misses it</label>
            <NumberList label="callouts (m before)" value={route.callouts_m as number[]} onChange={(v) => set(["route", "callouts_m"], v)} />
          </> : key === "add_ons" ? (
            Object.entries(value as Obj).map(([name, spec]) => (
              <div key={name}>
                <label className="check"><input type="checkbox" checked={spec != null}
                  onChange={(e) => set(["add_ons", name], e.target.checked ? choices.add_ons[name] : null)} /> {name.replace("_", " ")}</label>
                {spec != null && <div className="sub"><Fields value={spec as Obj} path={["add_ons", name]} set={set} /></div>}
              </div>
            ))
          ) : (
            <Fields value={value as Obj} path={[key]} set={set} />
          )}
        </fieldset>
      ))}
      <div className="editor-actions">
        <button disabled={!changed || computing} onClick={() => run(draft as unknown as Scenario)}>Run this</button>
        <button disabled={!changed} onClick={() => { setDraft(scenario as unknown as Obj); setVersion((v) => v + 1); }}>Undo edits</button>
        <button onClick={doSave} title="Writes the scenario under its name to scenarios/saved/">Save as “{draft.name as string}”</button>
        {saved && <span className="hint">Saved to scenarios/saved/; it is in the scenario list now.</span>}
        {saveError && <span className="error">{saveError}</span>}
      </div>
    </div>
  );
}

// One input per number, checkbox per yes/no, and a nested group per sub-object.
function Fields({ value, path, set }: { value: Obj; path: string[]; set: (p: string[], v: unknown) => void }) {
  return <>
    {Object.entries(value).filter(([k]) => !HIDDEN.includes(k)).map(([k, v]) => {
      const p = [...path, k];
      const label = k.replace(/_/g, " ");
      if (typeof v === "number") {
        return <label key={k}>{label} <input type="number" step="any" defaultValue={v}
          onChange={(e) => { if (!isNaN(e.target.valueAsNumber)) set(p, e.target.valueAsNumber); }} /></label>;
      }
      if (typeof v === "boolean") return <label key={k} className="check"><input type="checkbox" checked={v} onChange={(e) => set(p, e.target.checked)} /> {label}</label>;
      if (typeof v === "string") return <label key={k}>{label} <input defaultValue={v} onChange={(e) => set(p, e.target.value)} /></label>;
      if (Array.isArray(v) && v.length && v.every((x) => typeof x === "number")) return <NumberList key={k} label={label} value={v} onChange={(x) => set(p, x)} />;
      if (Array.isArray(v)) {
        return <label key={k}>{label} <input defaultValue={JSON.stringify(v)} title="JSON, e.g. [{&quot;start_m&quot;: 1000, &quot;end_m&quot;: 2000}]"
          onChange={(e) => { try { set(p, JSON.parse(e.target.value)); } catch { /* still typing */ } }} /></label>;
      }
      if (v && typeof v === "object") return <div key={k} className="sub"><span className="sub-name">{label}</span><Fields value={v as Obj} path={p} set={set} /></div>;
      return null;
    })}
  </>;
}

function NumberList({ label, value, onChange }: { label: string; value: number[]; onChange: (v: number[]) => void }) {
  return <label>{label} <input defaultValue={value.join(", ")}
    onChange={(e) => onChange(e.target.value.split(",").map((x) => x.trim()).filter(Boolean).map(Number).filter((x) => !isNaN(x)))} /></label>;
}

function setIn(obj: unknown, path: string[], value: unknown): unknown {
  if (!path.length) return value;
  const [head, ...rest] = path;
  const o = (obj ?? {}) as Obj;
  return { ...o, [head]: setIn(o[head], rest, value) };
}
