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

    const stateObj = this._hass.states[this._config.entity];
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

window.customCards = window.customCards || [];
window.customCards.push({
  type: "handball-tournament-table-card",
  name: "Handball: Turnier Tabelle",
  description:
    "Zeigt die Tabelle eines Handball-Turniers (sensor.*_tabelle) an.",
  preview: false,
});
