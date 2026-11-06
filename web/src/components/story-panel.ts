/**
 * Human story anchor — prominent "Meet block group …" card on the map.
 * Real prepared-data narrative only (see lib/story.ts). Dismissible for
 * the session; "See its report card" deep-links via shared state (which
 * also updates the shareable URL).
 */
import { busSvg } from "../lib/mascot";
import { buildNarratorSteps } from "../lib/narrator";
import { paintSketch } from "../lib/sketch";
import { actions, getState } from "../state";
import { storyNarrative, toStoryAnchor } from "../lib/story";
import type {
  EquityFeature,
  RecommendationFeature,
  SensitivityRecord,
} from "../types";

interface StoryPanelOptions {
  container: HTMLElement;
  feature: EquityFeature;
  recommendations: RecommendationFeature[];
  sensitivity: SensitivityRecord[];
}

export class StoryPanel {
  private container: HTMLElement;
  private feature: EquityFeature;
  private recommendations: RecommendationFeature[];
  private sensitivity: SensitivityRecord[];
  private narrateStep = 0;
  private narrateTimer: number | null = null;

  constructor(options: StoryPanelOptions) {
    this.container = options.container;
    this.feature = options.feature;
    this.recommendations = options.recommendations;
    this.sensitivity = options.sensitivity;

    this.container.classList.add("dn-story", "sketch-card");
    this.container.setAttribute("aria-label", "Featured human story");

    const anchor = toStoryAnchor(this.feature);
    const nRecs = this.recommendations.filter((f) =>
      (f.properties.geoids ?? []).includes(anchor.geoid),
    ).length;

    this.container.innerHTML = `
      <div class="dn-story-head">
        <span class="dn-story-mascot" aria-hidden="true">${busSvg({ size: 34 })}</span>
        <div class="dn-story-head-text">
          <div class="dn-story-kicker">A real neighborhood</div>
          <div class="dn-story-title">Meet block group ${anchor.geoid}</div>
        </div>
        <button class="dn-story-close" type="button" aria-label="Dismiss story card">×</button>
      </div>
      <p class="dn-story-text">${storyNarrative(anchor, nRecs)}</p>
      <div class="dn-story-actions">
        <button class="dn-btn dn-narrate-toggle" type="button" aria-expanded="false">Hear the trip</button>
        <button class="dn-btn dn-story-cta" type="button">See its report card</button>
      </div>
      <div class="dn-narrate" hidden>
        <div class="dn-narrate-scene" aria-hidden="true">
          <div class="dn-narrate-track">
            <svg class="dn-narrate-route" viewBox="0 0 300 24" preserveAspectRatio="none" focusable="false"><path d="M4 12 Q 25 5 52 12 T 104 12 T 156 12 T 208 12 T 260 12 T 296 12" /></svg>
            <span class="dn-narrate-bus">${busSvg({ size: 34 })}</span>
          </div>
        </div>
        <div class="dn-narrate-body" aria-live="polite"></div>
        <div class="dn-narrate-dots" aria-hidden="true"></div>
        <div class="dn-narrate-actions">
          <button class="dn-btn dn-narrate-play" type="button">Play</button>
          <button class="dn-btn dn-narrate-back" type="button" hidden>Back</button>
          <button class="dn-btn dn-narrate-next" type="button">Next</button>
        </div>
      </div>`;

    const close = this.container.querySelector<HTMLButtonElement>(".dn-story-close")!;
    close.addEventListener("click", () => {
      this.container.remove();
    });

    const cta = this.container.querySelector<HTMLButtonElement>(".dn-story-cta")!;
    cta.addEventListener("click", () => {
      actions.selectGeoid(anchor.geoid);
      if (getState().view !== "map") actions.setView("map");
    });

    this.wireNarrator();
    // Container IS the sketch host (querySelectorAll would miss self).
    paintSketch(this.container);
  }

  private wireNarrator(): void {
    const toggle = this.container.querySelector<HTMLButtonElement>(".dn-narrate-toggle")!;
    const panel = this.container.querySelector<HTMLElement>(".dn-narrate")!;
    toggle.addEventListener("click", () => {
      const open = panel.hidden;
      panel.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      toggle.textContent = open ? "Close the trip" : "Hear the trip";
      if (open) {
        this.narrateStep = 0;
        this.renderNarrate();
        requestAnimationFrame(() => {
          const bus = this.container.querySelector<HTMLElement>(".dn-narrate-bus");
          const scene = this.container.querySelector<HTMLElement>(".dn-narrate-scene");
          if (bus && scene) {
            bus.style.setProperty(
              "--narrate-distance",
              `${Math.max(scene.clientWidth - 44, 80)}px`,
            );
          }
        });
      } else {
        this.stopNarrate();
      }
    });

    this.container.querySelector<HTMLButtonElement>(".dn-narrate-play")!.addEventListener("click", () => {
      this.togglePlay();
    });
    this.container.querySelector<HTMLButtonElement>(".dn-narrate-next")!.addEventListener("click", () => {
      const n = this.narratorSteps().length;
      if (this.narrateStep < n - 1) {
        this.narrateStep += 1;
        this.renderNarrate();
        this.driveToStep();
      } else {
        this.stopNarrate();
      }
    });
    this.container.querySelector<HTMLButtonElement>(".dn-narrate-back")!.addEventListener("click", () => {
      if (this.narrateStep > 0) {
        this.narrateStep -= 1;
        this.renderNarrate();
        this.driveToStep();
      }
    });
  }

  private narratorSteps(): ReturnType<typeof buildNarratorSteps> {
    return buildNarratorSteps(this.feature, this.recommendations, this.sensitivity);
  }

  private narratorReducedMotion(): boolean {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  private stopNarrate(): void {
    if (this.narrateTimer !== null) {
      window.clearInterval(this.narrateTimer);
      this.narrateTimer = null;
    }
    const play = this.container.querySelector<HTMLButtonElement>(".dn-narrate-play");
    if (play) play.textContent = "Play";
  }

  private togglePlay(): void {
    const play = this.container.querySelector<HTMLButtonElement>(".dn-narrate-play")!;
    if (this.narrateTimer !== null) {
      this.stopNarrate();
      return;
    }
    if (this.narratorReducedMotion()) {
      // Reduced motion: static — step all the way to the end, no drive.
      this.narrateStep = this.narratorSteps().length - 1;
      this.renderNarrate();
      return;
    }
    play.textContent = "Pause";
    this.driveToStep();
    this.narrateTimer = window.setInterval(() => {
      if (this.narrateStep >= this.narratorSteps().length - 1) {
        this.stopNarrate();
        return;
      }
      this.narrateStep += 1;
      this.renderNarrate();
      this.driveToStep();
    }, 2300);
  }

  private driveToStep(): void {
    const bus = this.container.querySelector<HTMLElement>(".dn-narrate-bus");
    const scene = this.container.querySelector<HTMLElement>(".dn-narrate-scene");
    if (!bus) return;
    const n = this.narratorSteps().length;
    const dist = scene ? Math.max(scene.clientWidth - 44, 80) : 120;
    const fraction = n <= 1 ? 1 : this.narrateStep / (n - 1);
    if (this.narratorReducedMotion()) {
      bus.style.setProperty("--narrate-distance", "0px");
      return;
    }
    bus.style.setProperty("--narrate-distance", "0px");
    // Two-frame restart so the transition replays per step.
    requestAnimationFrame(() => {
      bus.style.transition = "none";
      void bus.offsetWidth;
      bus.style.transition = "";
      bus.style.setProperty("--narrate-distance", `${Math.round(dist * 0.85 * fraction)}px`);
    });
  }

  private renderNarrate(): void {
    const steps = this.narratorSteps();
    const step = steps[this.narrateStep] ?? steps[0]!;
    const body = this.container.querySelector<HTMLElement>(".dn-narrate-body")!;
    body.innerHTML =
      `<div class="dn-narrate-kicker">Step ${this.narrateStep + 1} of ${steps.length} · ${step.kicker}</div>` +
      `<div class="dn-narrate-claim">${step.claim}</div>` +
      `<p class="dn-narrate-detail">${step.detail}</p>`;
    body.classList.remove("dn-narrate-enter");
    void body.offsetWidth;
    body.classList.add("dn-narrate-enter");

    const dots = this.container.querySelector<HTMLElement>(".dn-narrate-dots")!;
    dots.innerHTML = steps
      .map((_, i) => `<span class="dn-tour-dot${i === this.narrateStep ? " is-active" : ""}"></span>`)
      .join("");

    const back = this.container.querySelector<HTMLButtonElement>(".dn-narrate-back")!;
    const next = this.container.querySelector<HTMLButtonElement>(".dn-narrate-next")!;
    back.hidden = this.narrateStep === 0;
    next.textContent = this.narrateStep === steps.length - 1 ? "Done" : "Next";
  }
}
