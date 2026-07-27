/**
 * handball-tournament-table-card
 *
 * Lovelace card for displaying a handball tournament table.
 *
 * Config:
 *   type: custom:handball-tournament-table-card
 *   entity: sensor.<tournament>_tabelle
 *   title: "Meine Liga"          # optional override
 *   highlight_team: "TSV Foo"    # optional – highlights a specific team row
 *   show_logo: true              # optional, default true
 */
class HandballTournamentTableCard extends HTMLElement {
  static async getConfigElement() {
    return document.createElement("handball-tournament-table-card-editor");
  }

  static getStubConfig() {
    return { entity: "sensor.handball_tournament_table" };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("handball-tournament-table-card: 'entity' is required");
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

  _render() {
    if (!this._hass || !this._config) return;

    let stateObj = this._hass.states[this._config.entity];
    if (!stateObj && this._config.entity === this.constructor.getStubConfig().entity) {
      stateObj = {
        attributes: {
          tournament_name: "Oberliga Nord",
          organization: "HBFV",
          tournament_acronym: "OLN",
          table: [
            {
              position: 1,
              team_name: "SV Hafen",
              games_played: 18,
              wins: 15,
              draws: 1,
              losses: 2,
              goals_scored: 542,
              goals_conceded: 488,
              goal_difference: 54,
              points: "31:5",
              promoted: true,
            },
            {
              position: 2,
              team_name: "TSV Musterstadt",
              games_played: 18,
              wins: 13,
              draws: 2,
              losses: 3,
              goals_scored: 531,
              goals_conceded: 497,
              goal_difference: 34,
              points: "28:8",
            },
            {
              position: 3,
              team_name: "TV Nordstadt",
              games_played: 18,
              wins: 10,
              draws: 2,
              losses: 6,
              goals_scored: 510,
              goals_conceded: 503,
              goal_difference: 7,
              points: "22:14",
            },
            {
              position: 12,
              team_name: "HSG Tal",
              games_played: 18,
              wins: 2,
              draws: 1,
              losses: 15,
              goals_scored: 461,
              goals_conceded: 575,
              goal_difference: -114,
              points: "5:31",
              relegated: true,
            },
          ],
        },
      };
    }

    if (!stateObj) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding:16px;color:var(--error-color)">
            Entity <code>${this._config.entity}</code> not found.
          </div>
        </ha-card>`;
      return;
    }

    const attrs = stateObj.attributes;
    const table = attrs.table || [];
    const tournamentName =
      this._config.title || attrs.tournament_name || "Tabelle";
    const highlightTeam = this._config.highlight_team || null;
    const showLogo = this._config.show_logo !== false;

    const rows = table
      .map((row) => {
        const isHighlighted =
          highlightTeam &&
          row.team_name &&
          row.team_name.trim().toLowerCase() ===
            highlightTeam.trim().toLowerCase();
        const promoted = row.promoted;
        const relegated = row.relegated;

        let rowClass = "table-row";
        if (isHighlighted) rowClass += " highlighted";
        else if (promoted) rowClass += " promoted";
        else if (relegated) rowClass += " relegated";

        const logoHtml =
          showLogo && row.team_logo
            ? `<img src="${row.team_logo}" alt="" class="team-logo" loading="lazy">`
            : `<span class="team-logo-placeholder"></span>`;

        const rawDiff = Number(row.goal_difference);
        const goalDiff = isNaN(rawDiff)
          ? row.goal_difference
          : rawDiff > 0
          ? `+${rawDiff}`
          : rawDiff;

        return `
          <tr class="${rowClass}">
            <td class="pos">${row.position}</td>
            <td class="team">
              ${showLogo ? logoHtml : ""}
              <span class="team-name">${row.team_name || "–"}</span>
            </td>
            <td>${row.games_played ?? "–"}</td>
            <td class="wins">${row.wins ?? "–"}</td>
            <td class="draws">${row.draws ?? "–"}</td>
            <td class="losses">${row.losses ?? "–"}</td>
            <td class="goals">${row.goals_scored ?? "–"}:${
          row.goals_conceded ?? "–"
        }</td>
            <td class="td ${rawDiff > 0 ? "positive" : rawDiff < 0 ? "negative" : ""}">${goalDiff}</td>
            <td class="points">${row.points ?? "–"}</td>
          </tr>`;
      })
      .join("");

    const emptyRow = `
      <tr>
        <td colspan="9" class="empty">Keine Tabellendaten verfügbar</td>
      </tr>`;

    const subtitle = [attrs.organization, attrs.tournament_acronym]
      .filter(Boolean)
      .join(" · ");

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { overflow: hidden; }

        .card-header {
          padding: 12px 16px 10px;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.1));
        }
        .card-header h2 {
          margin: 0 0 2px;
          font-size: 1rem;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .card-header .subtitle {
          font-size: 0.72rem;
          color: var(--secondary-text-color);
        }

        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.82rem;
        }
        thead th {
          padding: 5px 4px;
          text-align: center;
          color: var(--secondary-text-color);
          font-weight: 500;
          font-size: 0.7rem;
          border-bottom: 2px solid var(--divider-color, rgba(0,0,0,0.15));
          user-select: none;
        }
        thead th.team-col {
          text-align: left;
          padding-left: ${showLogo ? "6px" : "8px"};
        }

        tbody tr {
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.06));
        }
        tbody tr:last-child { border-bottom: none; }

        td {
          padding: 5px 4px;
          text-align: center;
          color: var(--primary-text-color);
        }
        td.pos {
          color: var(--secondary-text-color);
          width: 24px;
          font-variant-numeric: tabular-nums;
        }
        td.team {
          text-align: left;
          padding-left: 4px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        td.points {
          font-weight: 700;
          font-variant-numeric: tabular-nums;
        }
        td.goals {
          font-variant-numeric: tabular-nums;
          white-space: nowrap;
        }
        td.td {
          font-variant-numeric: tabular-nums;
        }
        td.td.positive { color: #4caf50; }
        td.td.negative { color: #f44336; }
        td.wins  { color: #4caf50; }
        td.losses { color: #f44336; }

        .team-logo {
          width: 20px;
          height: 20px;
          object-fit: contain;
          flex-shrink: 0;
          vertical-align: middle;
        }
        .team-logo-placeholder {
          display: inline-block;
          width: 20px;
          height: 20px;
          flex-shrink: 0;
        }
        .team-name {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 160px;
        }

        tr.highlighted td {
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, #fff) !important;
        }
        tr.promoted {
          box-shadow: inset 3px 0 0 #4caf50;
        }
        tr.relegated {
          box-shadow: inset 3px 0 0 #f44336;
        }

        td.empty {
          text-align: center;
          padding: 20px;
          color: var(--secondary-text-color);
        }
      </style>
      <ha-card>
        <div class="card-header">
          <h2>${tournamentName}</h2>
          ${subtitle ? `<div class="subtitle">${subtitle}</div>` : ""}
        </div>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th class="team-col">Mannschaft</th>
              <th title="Spiele gespielt">Sp</th>
              <th title="Siege">S</th>
              <th title="Unentschieden">U</th>
              <th title="Niederlagen">N</th>
              <th title="Tore">Tore</th>
              <th title="Tordifferenz">TD</th>
              <th title="Punkte">Pkt</th>
            </tr>
          </thead>
          <tbody>
            ${rows || emptyRow}
          </tbody>
        </table>
      </ha-card>`;
  }

  getCardSize() {
    const table =
      this._hass?.states[this._config?.entity]?.attributes?.table || [];
    return Math.max(3, table.length + 2);
  }
}

customElements.define(
  "handball-tournament-table-card",
  HandballTournamentTableCard
);

class HandballTournamentTableCardEditor extends HTMLElement {
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
    let value;

    if (target.type === "checkbox") {
      value = target.checked;
    } else {
      value = target.value?.trim();
    }

    if (key === "show_logo") {
      if (value === true) {
        delete config.show_logo;
      } else {
        config.show_logo = false;
      }
    } else if (value) {
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
        input[type="text"] {
          font: inherit;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.2));
          border-radius: 8px;
          padding: 8px 10px;
          box-sizing: border-box;
          width: 100%;
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .checkbox-row label {
          color: var(--primary-text-color);
        }
      </style>
      <div class="grid">
        <div class="field">
          <label for="entity">Entity: Tabelle</label>
          <input
            id="entity"
            type="text"
            data-key="entity"
            value="${this._config?.entity ?? ""}"
            list="tournament-sensor-entities"
            placeholder="sensor.mein_turnier_tabelle"
          />
        </div>

        <div class="field">
          <label for="title">Titel (optional)</label>
          <input
            id="title"
            type="text"
            data-key="title"
            value="${this._config?.title ?? ""}"
            placeholder="z. B. Oberliga Nord"
          />
        </div>

        <div class="field">
          <label for="highlight_team">Team hervorheben (optional)</label>
          <input
            id="highlight_team"
            type="text"
            data-key="highlight_team"
            value="${this._config?.highlight_team ?? ""}"
            placeholder="z. B. TSV Musterstadt"
          />
        </div>

        <div class="checkbox-row">
          <input
            id="show_logo"
            type="checkbox"
            data-key="show_logo"
            ${this._config?.show_logo !== false ? "checked" : ""}
          />
          <label for="show_logo">Team-Logos anzeigen</label>
        </div>
      </div>
      <datalist id="tournament-sensor-entities">
        ${sensorEntities.map((entityId) => `<option value="${entityId}"></option>`).join("")}
      </datalist>
    `;

    this.shadowRoot.querySelectorAll("input").forEach((input) => {
      input.addEventListener("change", this._onValueChanged.bind(this));
    });
  }
}

customElements.define(
  "handball-tournament-table-card-editor",
  HandballTournamentTableCardEditor
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "handball-tournament-table-card",
  name: "Handball: Turnier Tabelle",
  description:
    "Zeigt die Tabelle eines Handball-Turniers (sensor.*_tabelle) an.",
  preview: true,
});
