/**
 * Mascot — a hand-authored, cute-but-neutral "wobbly bus". Drawn with
 * deliberately imperfect paths (slight asymmetry) so it reads hand-made.
 * Kept dependency-free: it's plain inline SVG strings.
 *
 * Colors reuse the chrome tokens (amber accent, ink, paper) so the character
 * sits naturally inside the sketch theme. Used sparingly: header mark, boot
 * scene, and empty states.
 */

const INK = "#2c2822";
const AMBER = "#c4622d";
const AMBER_DEEP = "#a34e22";
const PAPER = "#fbf7ee";
const LIGHT = "#ffe9b0";

/** Front-facing bus. `size` is the rendered width; height keeps ratio. */
export function busSvg(opts: { cls?: string; size?: number } = {}): string {
  const size = opts.size ?? 64;
  const height = Math.round((size * 58) / 72);
  const cls = opts.cls ? ` class="${opts.cls}"` : "";
  return `<svg width="${size}" height="${height}" viewBox="0 0 72 58"${cls} aria-hidden="true" focusable="false">
  <!-- body -->
  <path d="M12 41 C10 41 8 39 8 37 L8 18 C8 13 12 9 17 9 Q36 6.5 55 9 C60 9 64 13 64 18 L64 37 C64 39 62 41 60 41 Z"
    fill="${AMBER}" stroke="${INK}" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M11 37 C20 34 52 34 61 37" fill="none" stroke="${INK}" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
  <!-- roof sign -->
  <rect x="29" y="4.5" width="14" height="4.5" rx="2" fill="${PAPER}" stroke="${INK}" stroke-width="1.6"/>
  <!-- windows -->
  <rect x="20" y="17.5" width="15" height="12" rx="4" fill="${PAPER}" stroke="${INK}" stroke-width="1.8"/>
  <rect x="39" y="17.5" width="14" height="12" rx="4" fill="${PAPER}" stroke="${INK}" stroke-width="1.8"/>
  <!-- eyes (in the windows) -->
  <ellipse cx="27.5" cy="25" rx="3.1" ry="4" fill="${INK}"/>
  <circle cx="26.4" cy="23.4" r="1.1" fill="#fff"/>
  <ellipse cx="46" cy="25" rx="3.1" ry="4" fill="${INK}"/>
  <circle cx="44.9" cy="23.4" r="1.1" fill="#fff"/>
  <!-- smile -->
  <path d="M37 31.5 Q39.5 34 42 31.5" fill="none" stroke="${INK}" stroke-width="1.8" stroke-linecap="round"/>
  <!-- headlights -->
  <circle cx="15.5" cy="33" r="2.6" fill="${LIGHT}" stroke="${INK}" stroke-width="1.4"/>
  <circle cx="56.5" cy="33" r="2.6" fill="${LIGHT}" stroke="${INK}" stroke-width="1.4"/>
  <!-- grille ticks -->
  <path d="M33 36 L33 40 M36 36 L36 40 M39 36 L39 40" stroke="${INK}" stroke-width="1.8" stroke-linecap="round" opacity="0.7"/>
  <!-- wheels -->
  <g class="dn-wheel"><circle cx="16.5" cy="50" r="7" fill="${INK}"/>
    <circle cx="16.5" cy="50" r="4.2" fill="${AMBER_DEEP}"/>
    <path d="M16.5 45.8 V48 M16.5 52 V54.2 M12.3 50 H14.6 M18.4 50 H20.7" stroke="${PAPER}" stroke-width="1.4" stroke-linecap="round"/></g>
  <g class="dn-wheel"><circle cx="55.5" cy="50" r="7" fill="${INK}"/>
    <circle cx="55.5" cy="50" r="4.2" fill="${AMBER_DEEP}"/>
    <path d="M55.5 45.8 V48 M55.5 52 V54.2 M51.3 50 H53.6 M57.4 50 H59.7" stroke="${PAPER}" stroke-width="1.4" stroke-linecap="round"/></g>
</svg>`;
}

/** Small header mark (simplified, no face). */
export function busMark(opts: { cls?: string; size?: number } = {}): string {
  const size = opts.size ?? 30;
  const height = Math.round((size * 58) / 72);
  const cls = opts.cls ? ` class="${opts.cls}"` : "";
  return `<svg width="${size}" height="${height}" viewBox="0 0 72 58"${cls} aria-hidden="true" focusable="false">
  <path d="M12 41 C10 41 8 39 8 37 L8 18 C8 13 12 9 17 9 Q36 6.5 55 9 C60 9 64 13 64 18 L64 37 C64 39 62 41 60 41 Z"
    fill="${AMBER}" stroke="${INK}" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="20" y="17.5" width="15" height="12" rx="4" fill="${PAPER}" stroke="${INK}" stroke-width="1.8"/>
  <rect x="39" y="17.5" width="14" height="12" rx="4" fill="${PAPER}" stroke="${INK}" stroke-width="1.8"/>
  <circle cx="15.5" cy="33" r="2.6" fill="${LIGHT}" stroke="${INK}" stroke-width="1.4"/>
  <circle cx="56.5" cy="33" r="2.6" fill="${LIGHT}" stroke="${INK}" stroke-width="1.4"/>
  <g class="dn-wheel"><circle cx="16.5" cy="50" r="7" fill="${INK}"/><circle cx="16.5" cy="50" r="4.2" fill="${AMBER_DEEP}"/></g>
  <g class="dn-wheel"><circle cx="55.5" cy="50" r="7" fill="${INK}"/><circle cx="55.5" cy="50" r="4.2" fill="${AMBER_DEEP}"/></g>
</svg>`;
}
