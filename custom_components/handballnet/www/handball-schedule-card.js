/**
 * handball-schedule-card
 *
 * Lovelace card to page through a tournament schedule matchday by matchday.
 *
 * Config:
 *   type: custom:handball-schedule-card
 *   entity: sensor.<tournament>_spielplan        # required (schedule sensor)
 *   table_entity: sensor.<tournament>_tabelle     # optional – adds team logos
 *   highlight_team: "HT NORDERSTEDT"              # optional – highlights matches
 *   title: "Spielplan"                            # optional
 *
 * The DOM skeleton is built once; only the match list is replaced, and only
 * when its markup actually changed, so logos do not flicker on hass updates.
 */
class HandballScheduleCard extends HTMLElement {
  static getStubConfig() {
    return { entity: "sensor.handball_tournament_spielplan" };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("handball-schedule-card: 'entity' is required");
    }
    this._config = config;
    this._index = null; // null = follow the current matchday
    this._lastListHtml = null;
    this._lastHeader = null;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    const watched = [
      hass.states[this._config.entity],
      this._config.table_entity ? hass.states[this._config.table_entity] : null,
    ];
    if (
      this._built &&
      this._lastStates &&
      watched.every((st, i) => st === this._lastStates[i])
    ) {
      return;
    }
    this._lastStates = watched;
    this._update();
  }

  // ── helpers ────────────────────────────────────────────────────────────

  _esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  _norm(name) {
    return String(name || "").trim().toUpperCase();
  }

  _logos() {
    const table =
      this._hass?.states[this._config.table_entity]?.attributes?.table || [];
    const map = {};
    for (const row of table) {
      if (row.team_name && row.team_logo) map[this._norm(row.team_name)] = row.team_logo;
    }
    return map;
  }

  _fmtDay(ms) {
    return new Date(ms).toLocaleDateString("de-DE", {
      weekday: "short",
      day: "2-digit",
      month: "2-digit",
    });
  }

  _fmtTime(ms) {
    return new Date(ms).toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  _fmtRange(start, end) {
    const opts = { day: "2-digit", month: "2-digit" };
    const a = new Date(start).toLocaleDateString("de-DE", opts);
    const b = new Date(end).toLocaleDateString("de-DE", opts);
    return a === b ? a : `${a} – ${b}`;
  }

  // ── rendering ──────────────────────────────────────────────────────────

  _build() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }
        .head {
          display: flex; align-items: center; gap: 8px;
          padding: 12px 12px 10px 16px;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
        }
        .titles { flex: 1; min-width: 0; }
        .title { margin: 0; font-size: 1rem; font-weight: 500; color: var(--primary-text-color); }
        .sub { font-size: 0.75rem; color: var(--secondary-text-color); }
        button {
          border: none; background: none; cursor: pointer;
          color: var(--primary-color); border-radius: 50%;
          width: 36px; height: 36px; font-size: 1.2rem; line-height: 1;
        }
        button:hover { background: var(--secondary-background-color, rgba(0,0,0,0.05)); }
        button[disabled] { color: var(--disabled-text-color, #bbb); cursor: default; background: none; }
        button.now { width: auto; border-radius: 16px; padding: 0 10px; font-size: 0.8rem; }
        .list { padding: 4px 0 8px; }
        .day {
          padding: 8px 16px 2px; font-size: 0.75rem; font-weight: 600;
          color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.03em;
        }
        .match {
          display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
          gap: 8px; padding: 6px 16px; font-size: 0.85rem; color: var(--primary-text-color);
        }
        .match.hl { background: rgba(var(--rgb-primary-color, 3,169,244), 0.12); font-weight: 600; }
        .team { display: flex; align-items: center; gap: 6px; min-width: 0; }
        .team.home { justify-content: flex-end; text-align: right; }
        .team span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .logo { width: 20px; height: 20px; object-fit: contain; flex-shrink: 0; }
        .score {
          min-width: 56px; text-align: center; font-variant-numeric: tabular-nums;
          padding: 2px 6px; border-radius: 6px;
          background: var(--secondary-background-color, rgba(0,0,0,0.05));
        }
        .score.open { color: var(--secondary-text-color); font-weight: 400; }
        .empty { padding: 16px; text-align: center; color: var(--secondary-text-color); }
      </style>
      <ha-card>
        <div class="head">
          <button class="prev" title="Vorheriger Spieltag">&#8249;</button>
          <div class="titles">
            <div class="title"></div>
            <div class="sub"></div>
          </div>
          <button class="now" title="Aktueller Spieltag">Aktuell</button>
          <button class="next" title="Nächster Spieltag">&#8250;</button>
        </div>
        <div class="list"></div>
      </ha-card>`;
    const root = this.shadowRoot;
    this._els = {
      title: root.querySelector(".title"),
      sub: root.querySelector(".sub"),
      list: root.querySelector(".list"),
      prev: root.querySelector(".prev"),
      next: root.querySelector(".next"),
      now: root.querySelector(".now"),
    };
    this._els.prev.addEventListener("click", () => this._step(-1));
    this._els.next.addEventListener("click", () => this._step(1));
    this._els.now.addEventListener("click", () => {
      this._index = null;
      this._update();
    });
    this._built = true;
  }

  _step(delta) {
    const attrs = this._hass?.states[this._config.entity]?.attributes || {};
    const days = attrs.matchdays || [];
    const current = this._index ?? attrs.current_matchday_index ?? 0;
    this._index = Math.min(Math.max(current + delta, 0), Math.max(days.length - 1, 0));
    this._update();
  }

  _update() {
    if (!this._hass || !this._config) return;
    if (!this._built) this._build();

    const stateObj = this._hass.states[this._config.entity];
    const attrs = stateObj?.attributes || {};
    const days = attrs.matchdays || [];

    if (!stateObj || !days.length) {
      this._setHeader(this._config.title || "Spielplan", stateObj ? "Keine Spiele" : `Entität ${this._config.entity} nicht gefunden`);
      this._setList(`<div class="empty">Keine Spieldaten verfügbar</div>`);
      this._els.prev.disabled = this._els.next.disabled = true;
      return;
    }

    const current = Math.min(attrs.current_matchday_index ?? 0, days.length - 1);
    const index = Math.min(this._index ?? current, days.length - 1);
    const day = days[index];

    const title = this._config.title ? `${this._config.title} · ${day.label}` : day.label;
    const sub = `${this._fmtRange(day.start, day.end)} · ${index + 1} von ${days.length}`;
    this._setHeader(title, sub);
    this._els.prev.disabled = index <= 0;
    this._els.next.disabled = index >= days.length - 1;
    this._els.now.disabled = index === current;

    const logos = this._config.table_entity ? this._logos() : {};
    const highlight = this._norm(this._config.highlight_team);

    let lastDay = "";
    const rows = [];
    for (const m of day.matches || []) {
      const dayLabel = this._fmtDay(m.starts_at);
      if (dayLabel !== lastDay) {
        rows.push(`<div class="day">${this._esc(dayLabel)}</div>`);
        lastDay = dayLabel;
      }
      const played =
        typeof m.home_goals === "number" && typeof m.away_goals === "number";
      const score = played
        ? `${m.home_goals}:${m.away_goals}`
        : this._fmtTime(m.starts_at);
      const hl =
        highlight &&
        (this._norm(m.home) === highlight || this._norm(m.away) === highlight);
      const logo = (name) => {
        const url = logos[this._norm(name)];
        return url
          ? `<img class="logo" src="${this._esc(url)}" alt="" width="20" height="20" decoding="sync">`
          : "";
      };
      rows.push(`
        <div class="match${hl ? " hl" : ""}" title="${this._esc(m.field || "")}">
          <div class="team home"><span>${this._esc(m.home)}</span>${logo(m.home)}</div>
          <div class="score${played ? "" : " open"}">${this._esc(score)}</div>
          <div class="team">${logo(m.away)}<span>${this._esc(m.away)}</span></div>
        </div>`);
    }
    this._setList(rows.join(""));
  }

  _setHeader(title, sub) {
    const key = `${title}|${sub}`;
    if (key === this._lastHeader) return;
    this._lastHeader = key;
    this._els.title.textContent = title;
    this._els.sub.textContent = sub;
  }

  _setList(html) {
    // Only touch the DOM when the markup differs: re-creating identical <img>
    // tags is what makes logos flicker.
    if (html === this._lastListHtml) return;
    this._lastListHtml = html;
    this._els.list.innerHTML = html;
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }
}

customElements.define("handball-schedule-card", HandballScheduleCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "handball-schedule-card",
  name: "Handball: Spielplan nach Spieltagen",
  description:
    "Blättert den Spielplan eines Turniers Spieltag für Spieltag durch (Ergebnisse und Anwurfzeiten).",
  preview: false,
});
