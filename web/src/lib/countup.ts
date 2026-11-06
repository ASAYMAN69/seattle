/**
 * Metric count-up — a gentle ease-out number tween for what-if and report
 * card metrics. Uses WAAPI-free rAF (cheap, runs off the main thread
 * budget). Respects `prefers-reduced-motion` (sets final value
 * instantly) and cancels any previous tween on the same element
 * (slider drags re-render rapidly).
 */

const active = new WeakMap<HTMLElement, number>();

export interface CountUpOptions {
  duration?: number;
  format?: (value: number) => string;
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Animate `el` from its current displayed number (or 0) to `target`,
 * formatting each frame with `format`. On reduced motion, or when the
 * target is not finite, the final value is set immediately.
 */
export function countUpTo(
  el: HTMLElement,
  target: number,
  opts: CountUpOptions = {},
): void {
  const format = opts.format ?? ((v: number) => String(Math.round(v)));
  const duration = opts.duration ?? 650;

  const prev = active.get(el);
  if (prev !== undefined) cancelAnimationFrame(prev);

  if (!Number.isFinite(target) || prefersReducedMotion() || duration <= 0) {
    el.textContent = format(target);
    active.delete(el);
    return;
  }

  // Start from 0 so the number feels like it's "arriving" rather than
  // crawling between arbitrary previous values.
  const from = 0;
  const start = performance.now();

  const tick = (now: number): void => {
    const t = Math.min((now - start) / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - t, 3);
    const value = from + (target - from) * eased;
    el.textContent = format(value);
    if (t < 1) {
      active.set(el, requestAnimationFrame(tick));
    } else {
      el.textContent = format(target);
      active.delete(el);
    }
  };

  active.set(el, requestAnimationFrame(tick));
}
