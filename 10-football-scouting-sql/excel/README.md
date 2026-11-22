# Scouting shortlist in Excel

`scouting_shortlist.xlsx` puts the 46 wide forwards from this project into a workbook a scout or analyst can use without code. It's built by `../build_excel.py` from `../tableau/players.csv`, so every number matches the SQL output.

| Sheet | What it shows | Excel skill |
|---|---|---|
| **Players** | One row per player: club, club finish, minutes, score, the six per-90 metrics, goals, xG, assists and xA | Excel Table (`tbl_players`), structured references, frozen panes |
| **Pivot** | By club tier and club: number of players, average score, non-penalty goals, xG and assists. Totals: 46 players, 188 goals, 166.6 xG, 168 assists | PivotTable (count, average and sum) |
| **Lookup** | Pick a player in the yellow cell (drop-down list), and the card fills in: team, finish, rank, score, goals vs xG, assists vs xA and key per-90s, plus the next player in the ranking | `XLOOKUP` with a not-found value, data validation |
| **About** | Source, sheet guide and version note | |

**Check it:** the card opens on Dimitri Payet. It should show West Ham United, 7th, rank 2, score 81.8, 9 goals from 5.1 xG (+3.9), 12 assists from 10.9 xA, and De Bruyne as the next player.

**Version note:** `XLOOKUP` needs Excel 2021, Microsoft 365 or Google Sheets. Older Excel versions show `#NAME?` on the Lookup sheet. The other sheets work everywhere.

**Rebuild:** `python build_excel.py` from the project folder. It needs `openpyxl` and LibreOffice (`soffice`), because openpyxl can't create PivotTables, so LibreOffice adds the PivotTable and openpyxl adds the rest.

Data: StatsBomb Open Data (credit: StatsBomb).
