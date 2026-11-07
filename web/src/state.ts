/** Minimal pub/sub app state (vanilla, no framework). */
import type { LayerKey } from "./lib/colors";

export type ViewKey = "map" | "whatif" | "export";

export type BeforeAfter = "today" | "after";

export type TimeOfDay = "am_peak" | "off_peak";

export interface AppState {
  view: ViewKey;
  layer: LayerKey;
  selectedGeoid: string | null;
  beforeAfter: BeforeAfter;
  timeOfDay: TimeOfDay;
}

type Listener = (next: AppState, prev: AppState) => void;

const initialState: AppState = {
  view: "map",
  layer: "need_index",
  selectedGeoid: null,
  beforeAfter: "today",
  timeOfDay: "am_peak",
};

let state: AppState = { ...initialState };
const listeners = new Set<Listener>();

export function getState(): AppState {
  return { ...state };
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function set(patch: Partial<AppState>): void {
  const prev = state;
  const next = { ...state, ...patch };
  if (
    next.view === prev.view &&
    next.layer === prev.layer &&
    next.selectedGeoid === prev.selectedGeoid &&
    next.beforeAfter === prev.beforeAfter &&
    next.timeOfDay === prev.timeOfDay
  ) {
    return;
  }
  state = next;
  for (const fn of listeners) fn(next, prev);
}

export const actions = {
  setView: (view: ViewKey) => set({ view }),
  setLayer: (layer: LayerKey) => set({ layer }),
  selectGeoid: (geoid: string | null) => set({ selectedGeoid: geoid }),
  setBeforeAfter: (beforeAfter: BeforeAfter) => set({ beforeAfter }),
  setTimeOfDay: (timeOfDay: TimeOfDay) => set({ timeOfDay }),
  /** Atomic restore (used by deep-link boot): one notification, one render. */
  restore: (patch: Partial<AppState>) => set(patch),
};
