/**
 * Guided tour — lightweight first-visit overlay (3–4 steps) walking the
 * 90-second judge flow. Dismissible (×/Skip/Escape), "Don't show again"
 * persists via localStorage. Keyboard-operable: focus moves to the
 * dialog on open, Escape closes, focus returns to the invoker.
 * Reduced motion: steps swap instantly (see style.css).
 */
import { busSvg } from "../lib/mascot";
import { paintSketchBoxes } from "../lib/sketch";

const STORAGE_KEY = "dn_onboarding_dismissed";

interface TourStep {
  title: string;
  body: string;
}

const STEPS: TourStep[] = [
  {
    title: "1 · Start at the map",
    body: "Red block groups need more than transit gives them. Blue are better served. Click any block group to open its report card — that is the whole demo.",
  },
  {
    title: "2 · Read the report card",
    body: "Grades A to F plus real numbers: poverty share, zero-car households, income. Wobbly but accurate.",
  },
  {
    title: "3 · Ask “what if?”",
    body: "In What-if, pick a corridor and drag the frequency slider. You will see who benefits and how many minutes the wait drops.",
  },
  {
    title: "4 · Take the numbers",
    body: "Export real CSVs for your deck, or press “Copy link” up top to share this exact view with a judge.",
  },
];

export function shouldShowTour(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) !== "1";
  } catch {
    return true;
  }
}

export function persistTourDismissed(dontShowAgain: boolean): void {
  try {
    if (dontShowAgain) window.localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* private mode: tour may reappear; never trap the user */
  }
}

export class Onboarding {
  private root: HTMLElement;
  private index = 0;
  private previouslyFocused: HTMLElement | null = null;
  private onDone: (() => void) | null = null;

  constructor() {
    this.onDone = null;
    this.root = document.createElement("div");
    this.root.className = "dn-tour-root";
    this.root.setAttribute("role", "dialog");
    this.root.setAttribute("aria-modal", "true");
    this.root.setAttribute("aria-label", "Welcome tour");

    this.root.innerHTML = `
      <div class="dn-tour-backdrop" aria-hidden="true"></div>
      <div class="dn-tour sketch-card">
        <div class="dn-tour-head">
          <span class="dn-tour-mascot" aria-hidden="true">${busSvg({ size: 36 })}</span>
          <h2 class="dn-tour-title">Seattle by bus, in 90 seconds</h2>
          <button class="dn-tour-close" type="button" aria-label="Close tour">×</button>
        </div>
        <div class="dn-tour-body" tabindex="-1"></div>
        <div class="dn-tour-dots" aria-hidden="true">${STEPS.map(
          (_, i) => `<span class="dn-tour-dot" data-i="${i}"></span>`,
        ).join("")}</div>
        <div class="dn-tour-actions">
          <button class="dn-btn is-secondary dn-tour-skip" type="button">Skip</button>
          <label class="dn-tour-again"><input type="checkbox" /> Don’t show again</label>
          <span class="dn-tour-spacer"></span>
          <button class="dn-btn is-secondary dn-tour-back" type="button" hidden>Back</button>
          <button class="dn-btn dn-tour-next" type="button">Next</button>
        </div>
      </div>`;

    document.body.appendChild(this.root);
    paintSketchBoxes(this.root);
    this.wire();
    this.render();
  }

  private wire(): void {
    this.root.querySelector(".dn-tour-close")!.addEventListener("click", () => this.close(false));
    this.root.querySelector(".dn-tour-skip")!.addEventListener("click", () => this.close(false));
    this.root.querySelector(".dn-tour-next")!.addEventListener("click", () => {
      if (this.index < STEPS.length - 1) {
        this.index += 1;
        this.render();
      } else {
        this.close(true);
      }
    });
    this.root.querySelector(".dn-tour-back")!.addEventListener("click", () => {
      if (this.index > 0) {
        this.index -= 1;
        this.render();
      }
    });
    this.root.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.close(false);
      // Light keyboard nav: arrows step through (dialog focus stays put).
      if (e.key === "ArrowRight" && this.index < STEPS.length - 1) {
        this.index += 1;
        this.render();
      }
      if (e.key === "ArrowLeft" && this.index > 0) {
        this.index -= 1;
        this.render();
      }
    });
    this.root.querySelector(".dn-tour-backdrop")!.addEventListener("click", () => this.close(false));
  }

  private render(): void {
    const step = STEPS[this.index]!;
    const body = this.root.querySelector<HTMLElement>(".dn-tour-body")!;
    body.innerHTML = `<h3 class="dn-tour-step-title">${step.title}</h3><p class="dn-tour-step-copy">${step.body}</p>`;
    // Step transition: re-trigger the enter animation.
    body.classList.remove("dn-tour-step-enter");
    void body.offsetWidth;
    body.classList.add("dn-tour-step-enter");

    for (const dot of this.root.querySelectorAll<HTMLElement>(".dn-tour-dot")) {
      dot.classList.toggle("is-active", Number(dot.dataset.i) === this.index);
    }
    const back = this.root.querySelector<HTMLButtonElement>(".dn-tour-back")!;
    const next = this.root.querySelector<HTMLButtonElement>(".dn-tour-next")!;
    const skip = this.root.querySelector<HTMLButtonElement>(".dn-tour-skip")!;
    back.hidden = this.index === 0;
    next.textContent = this.index === STEPS.length - 1 ? "Done" : "Next";
    skip.hidden = this.index === STEPS.length - 1;
    paintSketchBoxes(this.root);
  }

  show(): void {
    this.previouslyFocused = document.activeElement as HTMLElement | null;
    const close = this.root.querySelector<HTMLButtonElement>(".dn-tour-close")!;
    requestAnimationFrame(() => close.focus());
  }

  close(_finished: boolean): void {
    const again = this.root.querySelector<HTMLInputElement>(".dn-tour-again input")!;
    persistTourDismissed(again.checked);
    this.root.remove();
    this.previouslyFocused?.focus?.();
    this.onDone?.();
    this.onDone = null;
  }
}
