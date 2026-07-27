/**
 * handball-team-card
 *
 * Lovelace card showing team position, next match, and live score.
 *
 * Config:
 *   type: custom:handball-team-card
 *   title: "SG Musterstadt"            # optional – overrides auto-detected name
 *   table_position_entity: sensor.xyz_tabellenplatz   # optional
 *   next_match_entity:     sensor.xyz_naechstes_spiel # optional
 *   live_ticker_entity:    sensor.xyz_live_ticker     # optional – shows live score
 */
class HandballTeamCard extends HTMLElement {
  static async getConfigElement() {
    return document.createElement("handball-team-card-editor");
  }

  static getStubConfig() {
    return {
      table_position_entity: "sensor.handball_team_table_position",
      next_match_entity: "sensor.handball_team_naechstes_spiel",
      live_ticker_entity: "sensor.handball_team_live_ticker",
    };
  }

  setConfig(config) {
    if (
      !config.table_position_entity &&
      !config.next_match_entity &&
      !config.live_ticker_entity
    ) {
      throw new Error(
        "handball-team-card: at least one of table_position_entity, next_match_entity, or live_ticker_entity is required"
      );
    }
    this._config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  // ── helpers ──────────────────────────────────────────────────────────────

  _state(entityId) {
    return entityId ? this._hass.states[entityId] ?? null : null;
  }

  _teamLogoHtml(team, cssClass) {
    if (!team) return "";
    return team.logo
      ? `<img src="${team.logo}" alt="${team.name || ""}" class="${cssClass}" loading="lazy">`
      : `<span class="${cssClass} placeholder"></span>`;
  }

  // ── sections ─────────────────────────────────────────────────────────────

  _renderLive(liveState) {
    if (!liveState || liveState.state !== "Live") return "";
    const matches = liveState.attributes.live_matches || [];
    if (!matches.length) return "";

    const m = matches[0];
    const hg = m.homeGoals ?? "–";
    const ag = m.awayGoals ?? "–";

    return `
      <div class="section live-section">
        <div class="live-badge">● LIVE</div>
        <div class="live-matchup">
          <div class="live-team">
            ${this._teamLogoHtml(m.homeTeam, "live-logo")}
            <span class="live-team-name">${m.homeTeam?.name ?? ""}</span>
          </div>
          <div class="live-score">${hg}&thinsp;:&thinsp;${ag}</div>
          <div class="live-team">
            ${this._teamLogoHtml(m.awayTeam, "live-logo")}
            <span class="live-team-name">${m.awayTeam?.name ?? ""}</span>
          </div>
        </div>
      </div>`;
  }

  _renderTablePosition(tableState) {
    if (!tableState) return "";
    const a = tableState.attributes;
    if (!a.position) return "";

    const rawDiff = Number(a.goal_difference);
    const diffLabel = isNaN(rawDiff)
      ? a.goal_difference ?? "–"
      : rawDiff > 0
      ? `+${rawDiff}`
      : rawDiff;
    const diffClass = rawDiff > 0 ? "positive" : rawDiff < 0 ? "negative" : "";

    return `
      <div class="section">
        <div class="section-title">Tabellenplatz</div>
        <div class="pos-row">
          <div class="rank-block">
            <span class="rank-num">${a.position}</span>
            <span class="rank-dot">.</span>
          </div>
          <div class="pos-stats">
            <div class="wdl-row">
              <div class="wdl-cell win">
                <span class="wdl-num">${a.wins ?? "–"}</span>
                <span class="wdl-lbl">S</span>
              </div>
              <div class="wdl-cell draw">
                <span class="wdl-num">${a.draws ?? "–"}</span>
                <span class="wdl-lbl">U</span>
              </div>
              <div class="wdl-cell loss">
                <span class="wdl-num">${a.losses ?? "–"}</span>
                <span class="wdl-lbl">N</span>
              </div>
            </div>
            <div class="meta-row">
              <span class="meta-item">
                <span class="meta-lbl">Sp</span>
                <span class="meta-val">${a.games_played ?? "–"}</span>
              </span>
              <span class="meta-item">
                <span class="meta-lbl">Tore</span>
                <span class="meta-val">${a.goals_scored ?? "–"}:${a.goals_conceded ?? "–"}</span>
              </span>
              <span class="meta-item">
                <span class="meta-lbl">TD</span>
                <span class="meta-val ${diffClass}">${diffLabel}</span>
              </span>
              <span class="meta-item points-item">
                <span class="meta-lbl">Pkt</span>
                <span class="meta-val points-val">${a.points ?? "–"}</span>
              </span>
            </div>
          </div>
        </div>
      </div>`;
  }

  _renderNextMatch(nextState) {
    if (!nextState) return "";
    const a = nextState.attributes;
    if (!a.home_team) return "";

    const home = a.home_team;
    const away = a.away_team;
    const dateStr = a.match_date || "";
    const field = a.field || "";

    return `
      <div class="section">
        <div class="section-title">Nächstes Spiel</div>
        ${dateStr ? `<div class="match-date">${dateStr}</div>` : ""}
        <div class="matchup">
          <div class="match-team">
            ${this._teamLogoHtml(home, "match-logo")}
            <span class="match-name">${home.name ?? ""}</span>
          </div>
          <div class="match-vs">vs</div>
          <div class="match-team">
            ${this._teamLogoHtml(away, "match-logo")}
            <span class="match-name">${away.name ?? ""}</span>
          </div>
        </div>
        ${field ? `<div class="match-field"><ha-icon icon="mdi:map-marker" style="--mdi-icon-size:14px"></ha-icon> ${field}</div>` : ""}
      </div>`;
  }

  // ── main render ──────────────────────────────────────────────────────────

  _render() {
    if (!this._hass || !this._config) return;

    let tableState = this._state(this._config.table_position_entity);
    let nextState = this._state(this._config.next_match_entity);
    let liveState = this._state(this._config.live_ticker_entity);

    if (!tableState && !nextState && !liveState) {
      tableState = {
        attributes: {
          team_name: "SG Musterstadt",
          position: 3,
          wins: 14,
          draws: 2,
          losses: 5,
          games_played: 21,
          goals_scored: 612,
          goals_conceded: 588,
          goal_difference: 24,
          points: "30:12",
        },
      };

      nextState = {
        attributes: {
          match_date: "Sa, 19:30 Uhr",
          field: "Sporthalle Musterstadt",
          home_team: { name: "SG Musterstadt" },
          away_team: { name: "TV Nordstadt" },
        },
      };
    }

    // Derive team name: config > table_position attributes > next_match state name
    const teamName =
      this._config.title ||
      tableState?.attributes?.team_name ||
      nextState?.attributes?.home_team?.name ||
      "Team";

    const isLive = liveState?.state === "Live";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }

        /* ── Header ── */
        .card-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.1));
        }
        .card-title {
          font-size: 1rem;
          font-weight: 500;
          color: var(--primary-text-color);
          flex: 1;
        }
        ${isLive ? `.live-chip { font-size: 0.65rem; font-weight: 700; color: #fff;
          background: var(--error-color, #db4437); border-radius: 4px;
          padding: 2px 6px; letter-spacing: 0.5px; }` : ""}

        /* ── Shared section ── */
        .section {
          padding: 10px 16px 12px;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.06));
        }
        .section:last-child { border-bottom: none; }
        .section-title {
          font-size: 0.68rem;
          text-transform: uppercase;
          letter-spacing: 0.6px;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
          font-weight: 500;
        }

        /* ── Live section ── */
        .live-section {
          background: linear-gradient(135deg,
            var(--error-color, #db4437) 0%,
            color-mix(in srgb, var(--error-color, #db4437) 80%, #000) 100%);
          color: #fff;
          padding: 12px 16px;
        }
        .live-section .section-title { color: rgba(255,255,255,0.75); }
        .live-badge {
          font-size: 0.68rem;
          font-weight: 700;
          letter-spacing: 1px;
          margin-bottom: 10px;
          color: rgba(255,255,255,0.9);
        }
        .live-matchup {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 4px;
        }
        .live-team {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 5px;
          flex: 1;
          min-width: 0;
        }
        .live-logo {
          width: 40px;
          height: 40px;
          object-fit: contain;
        }
        .live-logo.placeholder {
          display: inline-block;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
        }
        .live-team-name {
          font-size: 0.78rem;
          text-align: center;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          width: 100%;
          color: rgba(255,255,255,0.95);
        }
        .live-score {
          font-size: 2.2rem;
          font-weight: 700;
          color: #fff;
          padding: 0 8px;
          flex-shrink: 0;
          font-variant-numeric: tabular-nums;
          letter-spacing: -1px;
        }

        /* ── Table position ── */
        .pos-row {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .rank-block {
          display: flex;
          align-items: baseline;
          flex-shrink: 0;
          color: var(--primary-color, #03a9f4);
          line-height: 1;
        }
        .rank-num {
          font-size: 3.2rem;
          font-weight: 700;
          font-variant-numeric: tabular-nums;
        }
        .rank-dot { font-size: 1.6rem; font-weight: 500; }
        .pos-stats { flex: 1; min-width: 0; }

        .wdl-row {
          display: flex;
          gap: 6px;
          margin-bottom: 6px;
        }
        .wdl-cell {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 5px 4px;
          border-radius: 6px;
        }
        .wdl-cell.win  { background: rgba(76, 175, 80, 0.12); }
        .wdl-cell.draw { background: rgba(158, 158, 158, 0.12); }
        .wdl-cell.loss { background: rgba(244, 67, 54, 0.12); }
        .wdl-num {
          font-size: 1.15rem;
          font-weight: 600;
          color: var(--primary-text-color);
          font-variant-numeric: tabular-nums;
        }
        .wdl-lbl {
          font-size: 0.65rem;
          color: var(--secondary-text-color);
          font-weight: 500;
        }

        .meta-row {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .meta-item {
          display: flex;
          align-items: baseline;
          gap: 3px;
          font-size: 0.8rem;
        }
        .meta-lbl { color: var(--secondary-text-color); }
        .meta-val  { color: var(--primary-text-color); font-weight: 500; font-variant-numeric: tabular-nums; }
        .meta-val.positive { color: #4caf50; }
        .meta-val.negative { color: #f44336; }
        .points-item { margin-left: auto; }
        .points-val {
          color: var(--primary-color, #03a9f4);
          font-size: 1rem;
          font-weight: 700;
        }

        /* ── Next match ── */
        .match-date {
          font-size: 0.8rem;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        .matchup {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .match-team {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          flex: 1;
          min-width: 0;
        }
        .match-logo {
          width: 36px;
          height: 36px;
          object-fit: contain;
        }
        .match-logo.placeholder {
          display: inline-block;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: var(--divider-color, rgba(0,0,0,0.1));
        }
        .match-name {
          font-size: 0.78rem;
          text-align: center;
          color: var(--primary-text-color);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          width: 100%;
        }
        .match-vs {
          font-size: 0.72rem;
          color: var(--secondary-text-color);
          flex-shrink: 0;
          padding: 0 2px;
        }
        .match-field {
          font-size: 0.75rem;
          color: var(--secondary-text-color);
          margin-top: 7px;
          display: flex;
          align-items: center;
          gap: 3px;
        }
      </style>
      <ha-card>
        <div class="card-header">
          <span class="card-title">${teamName}</span>
          ${isLive ? '<span class="live-chip">LIVE</span>' : ""}
        </div>
        ${this._renderLive(liveState)}
        ${this._renderTablePosition(tableState)}
        ${this._renderNextMatch(nextState)}
      </ha-card>`;
  }

  getCardSize() {
    return 4;
  }
}

customElements.define("handball-team-card", HandballTeamCard);

class HandballTeamCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _onValueChanged(ev) {
    const target = ev.target;
    const key = target?.dataset?.key;
    if (!key) return;

    const config = { ...this._config };
    const value = target.value?.trim();

    if (value) {
      config[key] = value;
    } else {
      delete config[key];
    }

    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    const sensorEntities = Object.keys(this._hass?.states || {})
      .filter((entityId) => entityId.startsWith("sensor."))
      .sort((a, b) => a.localeCompare(b));

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .grid {
          display: grid;
          gap: 12px;
        }
        .field {
          display: grid;
          gap: 4px;
        }
        label {
          font-size: 0.78rem;
          color: var(--secondary-text-color);
        }
        input {
          font: inherit;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.2));
          border-radius: 8px;
          padding: 8px 10px;
          box-sizing: border-box;
          width: 100%;
        }
        .hint {
          font-size: 0.75rem;
          color: var(--secondary-text-color);
        }
      </style>
      <div class="grid">
        <div class="field">
          <label for="title">Titel (optional)</label>
          <input
            id="title"
            type="text"
            data-key="title"
            value="${this._config?.title ?? ""}"
            placeholder="z. B. SG Musterstadt"
          />
        </div>

        <div class="field">
          <label for="table_position_entity">Entity: Tabellenplatz</label>
          <input
            id="table_position_entity"
            type="text"
            data-key="table_position_entity"
            value="${this._config?.table_position_entity ?? ""}"
            list="team-sensor-entities"
            placeholder="sensor.mein_team_table_position"
          />
        </div>

        <div class="field">
          <label for="next_match_entity">Entity: Nächstes Spiel</label>
          <input
            id="next_match_entity"
            type="text"
            data-key="next_match_entity"
            value="${this._config?.next_match_entity ?? ""}"
            list="team-sensor-entities"
            placeholder="sensor.mein_team_naechstes_spiel"
          />
        </div>

        <div class="field">
          <label for="live_ticker_entity">Entity: Live Ticker</label>
          <input
            id="live_ticker_entity"
            type="text"
            data-key="live_ticker_entity"
            value="${this._config?.live_ticker_entity ?? ""}"
            list="team-sensor-entities"
            placeholder="sensor.mein_team_live_ticker"
          />
        </div>

        <div class="hint">
          Mindestens eine der drei Entity-Felder muss gesetzt sein.
        </div>
      </div>
      <datalist id="team-sensor-entities">
        ${sensorEntities.map((entityId) => `<option value="${entityId}"></option>`).join("")}
      </datalist>
    `;

    this.shadowRoot.querySelectorAll("input").forEach((input) => {
      input.addEventListener("change", this._onValueChanged.bind(this));
    });
  }
}

customElements.define("handball-team-card-editor", HandballTeamCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "handball-team-card",
  name: "Handball: Team Karte",
  description:
    "Zeigt Tabellenplatz, nächstes Spiel und optionalen Live-Score eines Handball-Teams.",
  preview: true,
});
