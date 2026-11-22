"""Build excel/scouting_shortlist.xlsx: the scouting pool with a real PivotTable and XLOOKUP formulas.

Usage:  python export_extracts.py && python build_excel.py

Needs openpyxl and LibreOffice (soffice on PATH, with its Python "uno" bridge): openpyxl
can't create PivotTables, so LibreOffice adds it, and openpyxl keeps it when it adds the rest.
Sheets: Players (an Excel Table), Pivot (by club tier and club), Lookup (pick a player; XLOOKUP
fills the card) and About.
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

HERE = Path(__file__).parent
OUT = HERE / "excel" / "scouting_shortlist.xlsx"
COLS = ["score_rank", "player", "team", "club_finish", "club_tier", "minutes", "score",
        "np_xg_90", "xa_90", "key_passes_90", "dribbles_won_90", "prog_carries_90", "box_passes_90",
        "np_goals", "np_xg", "assists", "xa"]


def write_players(path, players):
    wb = Workbook()
    ws = wb.active
    ws.title = "Players"
    ws.append(COLS)
    for row in players[COLS].itertuples(index=False):
        ws.append([v.item() if hasattr(v, "item") else v for v in row])
    wb.save(path)


def add_pivot(path, n_rows):
    """Open the file in headless LibreOffice and add a PivotTable (DataPilot) on a new sheet."""
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.table import CellAddress, CellRangeAddress

    def prop(name, value):
        p = PropertyValue()
        p.Name, p.Value = name, value
        return p

    profile = tempfile.mkdtemp()
    office = subprocess.Popen(["soffice", "--headless", "--norestore", f"-env:UserInstallation=file://{profile}",
                               "--accept=socket,host=127.0.0.1,port=2099;urp;"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        resolver = uno.getComponentContext().ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", uno.getComponentContext())
        for _ in range(60):
            try:
                ctx = resolver.resolve("uno:socket,host=127.0.0.1,port=2099;urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise SystemExit("LibreOffice did not start")
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(path)), "_blank", 0,
                                           (prop("Hidden", True),))
        sheets = doc.Sheets
        sheets.insertNewByName("Pivot", 1)
        src = CellRangeAddress()
        src.Sheet, src.StartColumn, src.StartRow, src.EndColumn, src.EndRow = 0, 0, 0, len(COLS) - 1, n_rows
        tables = sheets.getByIndex(1).getDataPilotTables()
        desc = tables.createDataPilotDescriptor()
        desc.setSourceRange(src)
        fields = desc.getDataPilotFields()
        ROW = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "ROW")
        DATA = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "DATA")
        COUNT = uno.Enum("com.sun.star.sheet.GeneralFunction", "COUNT")
        SUM = uno.Enum("com.sun.star.sheet.GeneralFunction", "SUM")
        AVERAGE = uno.Enum("com.sun.star.sheet.GeneralFunction", "AVERAGE")
        for name, orient, func in [("club_tier", ROW, None), ("team", ROW, None),
                                   ("player", DATA, COUNT), ("score", DATA, AVERAGE),
                                   ("np_goals", DATA, SUM), ("np_xg", DATA, SUM), ("assists", DATA, SUM)]:
            f = fields.getByIndex(COLS.index(name))
            f.Orientation = orient
            if func is not None:
                f.Function = func
        # The five values side by side as columns, not stacked under each club.
        desc.getDataLayoutField().Orientation = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "COLUMN")
        dest = CellAddress()
        dest.Sheet, dest.Column, dest.Row = 1, 0, 2
        tables.insertNewByName("ScoutingPivot", dest, desc)
        sheets.getByIndex(1).getCellByPosition(0, 0).setString(
            "Wide forwards by club tier and club: players, average score, non-penalty goals, xG and assists")
        doc.storeToURL(uno.systemPathToFileUrl(str(path)),
                       (prop("FilterName", "Calc MS Excel 2007 XML"), prop("Overwrite", True)))
        doc.close(True)
    finally:
        office.terminate()
        office.wait(timeout=30)
        shutil.rmtree(profile, ignore_errors=True)


def finish(path, players):
    """Add the Excel Table, the XLOOKUP card and the About sheet; openpyxl keeps the pivot."""
    wb = load_workbook(path)
    ws = wb["Players"]
    last = f"{chr(ord('A') + len(COLS) - 1)}{len(players) + 1}"
    tbl = Table(displayName="tbl_players", ref=f"A1:{last}")
    tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(tbl)
    ws.freeze_panes = "C2"
    for col, width in {"A": 11, "B": 34, "C": 22, "E": 13}.items():
        ws.column_dimensions[col].width = width

    lk = wb.create_sheet("Lookup", 2)
    lk["A1"] = "Player card: choose a player in B3, and XLOOKUP fills the rest from tbl_players."
    lk["A1"].font = Font(bold=True, size=12)
    lk["A3"], lk["B3"] = "Player", players.player.iloc[1]          # opens on the top target outside the top six
    lk["B3"].fill = PatternFill("solid", fgColor="FFF2CC")
    dv = DataValidation(type="list", formula1=f"=Players!$B$2:$B${len(players) + 1}", allow_blank=False)
    lk.add_data_validation(dv)
    dv.add("B3")
    card = [("Team", "team"), ("Club finish", "club_finish"), ("Score rank (of %d)" % len(players), "score_rank"),
            ("Scouting score", "score"), ("Minutes", "minutes"), ("Non-penalty goals", "np_goals"),
            ("Non-penalty xG", "np_xg"), ("Assists", "assists"), ("xA", "xa"),
            ("Key passes per 90", "key_passes_90"), ("Dribbles won per 90", "dribbles_won_90")]
    for i, (label, field) in enumerate(card, start=5):
        lk[f"A{i}"] = label
        lk[f"B{i}"] = f'=_xlfn.XLOOKUP($B$3,tbl_players[player],tbl_players[{field}],"not found")'
    r = 5 + len(card) + 1
    lk[f"A{r}"] = "Goals minus xG"
    lk[f"B{r}"] = "=B10-B11"
    lk[f"A{r + 2}"] = "Next player in the ranking"
    lk[f"B{r + 2}"] = ("=_xlfn.XLOOKUP(B7+1,tbl_players[score_rank],tbl_players[player],"
                       '"(none: last or tied)")')
    lk.column_dimensions["A"].width = 26
    lk.column_dimensions["B"].width = 34
    for row in lk.iter_rows(min_row=3, max_row=r + 2, max_col=2):
        for c in row:
            c.alignment = Alignment(horizontal="left")

    ab = wb.create_sheet("About")
    notes = [
        "Wide forward scouting shortlist: Premier League 2015/16",
        "Data: StatsBomb Open Data (credit: StatsBomb). Built by 10-football-scouting-sql/build_excel.py.",
        "",
        "Players: one row per wide forward with 900+ minutes on the wing (46). An Excel Table (tbl_players).",
        "Pivot: a PivotTable by club tier and club: players, average score, non-penalty goals, xG, assists.",
        "Lookup: pick a player in the yellow cell; XLOOKUP formulas fill the card from tbl_players.",
        "",
        "XLOOKUP needs Excel 2021 or Microsoft 365 (or Google Sheets). Older Excel shows #NAME?.",
        "Numbers match tableau/players.csv and the project's SQL output.",
    ]
    for i, line in enumerate(notes, start=1):
        ab[f"A{i}"] = line
    ab["A1"].font = Font(bold=True, size=12)
    ab.column_dimensions["A"].width = 110
    wb.active = wb.sheetnames.index("Lookup")
    wb.save(path)


def main():
    players = pd.read_csv(HERE / "tableau" / "players.csv")
    if shutil.which("soffice") is None:
        raise SystemExit("LibreOffice (soffice) is needed to create the PivotTable.")
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_name("_build.xlsx")
    write_players(tmp, players)
    add_pivot(tmp.resolve(), len(players))
    finish(tmp, players)
    os.replace(tmp, OUT)

    # Check: the pivot survived, and the formulas point at real columns.
    wb = load_workbook(OUT)
    pivots = wb["Pivot"]._pivots
    assert len(pivots) == 1, "PivotTable missing"
    lk = wb["Lookup"]
    fields = [c.value.split("tbl_players[")[2].split("]")[0] for c in lk["B"][4:15]]
    assert all(f in COLS for f in fields), fields
    print(f"Saved {OUT.relative_to(HERE)}: sheets {wb.sheetnames}, 1 PivotTable, "
          f"{len(fields) + 1} XLOOKUP formulas on Lookup")


if __name__ == "__main__":
    main()
