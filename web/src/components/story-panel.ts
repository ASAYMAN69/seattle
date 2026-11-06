/**
 * Human story anchor — prominent "Meet block group …" card on the map.
 * Real prepared-data narrative only (see lib/story.ts). Dismissible for
 * the session; "See its report card" deep-links via shared state (which
 * also updates the shareable URL).
 */
import { busSvg } from "../lib/mascot";
import { paintSketch } from "../lib/sketch";
import { actions, getState } from "../state";
import { storyNarrative, toStoryAnchor } from "../lib/story";
import type {
  EquityFeature,
  RecommendationFeature,
} from "../types";

interface StoryPanelOptions {
  container: HTMLElement;
  feature: EquityFeature;
  recommendations: RecommendationFeature[];
}

export class StoryPanel {
  private container: HTMLElement;
  private feature: EquityFeature;
  private recommendations: RecommendationFeature[];

  constructor(options: StoryPanelOptions) {
    this.container = options.container;
    this.feature = options.feature;
    this.recommendations = options.recommendations;

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
        <button class="dn-btn dn-story-cta" type="button">See its report card</button>
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

    // Container IS the sketch host (querySelectorAll would miss self).
    paintSketch(this.container);
  }
}
