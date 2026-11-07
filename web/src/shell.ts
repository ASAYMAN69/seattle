/**
 * App shell markup — the outer header/nav/ribbon and the main view
 * containers. Separate from boot logic (Task 010 modularization);
 * the bus mark is injected at boot (busMark needs the mascot lib).
 */
export const SHELL_HTML = `
  <header class="dn-header">
    <div class="dn-header-inner">
      <div class="dn-brand">
        <span class="dn-brand-mark" aria-hidden="true">__BUS_MARK__</span>
        <h1 class="dn-title">Seattle Transit Equity Index</h1>
      </div>
      <nav class="dn-nav" aria-label="Views">
        <button class="dn-navbtn" data-view="map" type="button" aria-current="page">Map explorer</button>
        <button class="dn-navbtn" data-view="whatif" type="button">What-if</button>
        <button class="dn-navbtn" data-view="export" type="button">Export</button>
      </nav>
      <div class="dn-header-actions">
        <button class="dn-copy" id="copy-link" type="button" aria-live="polite">Copy link</button>
      </div>
    </div>
    <div class="dn-ribbon">
      <div class="dn-meta dn-muted" id="city-summary"></div>
    </div>
  </header>

  <main class="dn-main">
    <section class="dn-view dn-view-map is-active" data-view="map">
      <div id="map" class="dn-map" role="application" aria-label="Seattle transit equity map"></div>
      <div class="dn-map-controls sketch-card">
        <div class="dn-ctl-section">
          <span class="dn-mapctl-label">Area layer</span>
          <div class="dn-layer-tabs-row" role="group" aria-label="Area layer"></div>
        </div>
        <div class="dn-ctl-pair">
          <div class="dn-ctl-half" role="group" aria-label="Time of day scenario">
            <span class="dn-mapctl-label" aria-hidden="true">Scenario</span>
            <div class="dn-beforeafter-row">
              <button class="tod-btn is-active" data-tod="am_peak" type="button" aria-pressed="true">AM peak</button>
              <button class="tod-btn" data-tod="off_peak" type="button" aria-pressed="false">Off-peak ✦</button>
            </div>
          </div>
          <div class="dn-ctl-half" role="group" aria-label="Before or after recommendations">
            <span class="dn-mapctl-label" aria-hidden="true">Before / after</span>
            <div class="dn-beforeafter-row">
              <button class="dn-ba-btn is-active" data-mode="today" type="button" aria-pressed="true">Today</button>
              <button class="dn-ba-btn" data-mode="after" type="button" aria-pressed="false">If recommendations ship</button>
            </div>
          </div>
        </div>
        <div class="dn-scenario-banner" id="scenario-banner" role="status" hidden></div>
        <div class="dn-delta-readout" id="delta-readout" hidden></div>
      </div>
      <div id="story"></div>
      <div id="scrim" class="dn-scrim" aria-hidden="true"></div>
      <div id="drilldown"></div>
    </section>
    <section class="dn-view" data-view="whatif">
      <div id="whatif" class="dn-view-inner"></div>
    </section>
    <section class="dn-view" data-view="export">
      <div id="export" class="dn-view-inner"></div>
    </section>
    <div id="boot-state" class="dn-boot" role="status"></div>
  </main>`;
