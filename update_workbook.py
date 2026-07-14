"""Run the top-broker search and write results directly into the Excel workbook.

Creates (or replaces) one tab per market named "<Market> Top Brokers" -
e.g. "Atlanta Top Brokers" - containing the #1 broker at each firm plus the
runners-up, formatted to match the rest of the workbook (bold header row,
Arial, frozen header, sized columns).

This does NOT touch any of the existing tabs (Florida, Nashville, the RCA
tabs, etc.) - it only adds/replaces the "<Market> Top Brokers" tabs.

Usage:
    python update_workbook.py --workbook "Recruiting_Workbook.xlsx"
    python update_workbook.py --workbook "Recruiting_Workbook.xlsx" --market atlanta

Requirements:
    pip install openpyxl requests beautifulsoup4
"""

import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).parent))
from config.markets import MARKETS
from top_brokers import process_market

COLUMNS = ["Company", "Rank", "Name", "Title", "City", "Website"]
COLUMN_WIDTHS = [26, 6, 24, 34, 20, 55]
HEADER_FONT = Font(name="Arial", size=11, bold=True)
DATA_FONT = Font(name="Aptos Narrow", size=11)


def tab_name_for_market(display_name):
    # Excel tab names can't exceed 31 characters or contain : \ / ? * [ ]
    name = f"{display_name} Top Brokers"
    for bad_char in r':\/?*[]':
        name = name.replace(bad_char, "-")
    return name[:31]


def write_market_tab(workbook, market_slug, output_rows):
    from config.markets import get_market
    display_name = get_market(market_slug)["display_name"]
    tab_name = tab_name_for_market(display_name)

    if tab_name in workbook.sheetnames:
        del workbook[tab_name]
    ws = workbook.create_sheet(tab_name)

    for col_idx, header in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT

    for row_idx, row in enumerate(output_rows, start=2):
        ws.cell(row=row_idx, column=1, value=row["company"]).font = DATA_FONT
        ws.cell(row=row_idx, column=2, value=row["rank"]).font = DATA_FONT
        ws.cell(row=row_idx, column=3, value=row["name"]).font = DATA_FONT
        ws.cell(row=row_idx, column=4, value=row["title"]).font = DATA_FONT
        ws.cell(row=row_idx, column=5, value=row["city"]).font = DATA_FONT
        ws.cell(row=row_idx, column=6, value=row["website"]).font = DATA_FONT

    for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.freeze_panes = "A2"
    return tab_name


def parse_arguments():
    parser = argparse.ArgumentParser(description="Write top-broker results into the Excel workbook.")
    parser.add_argument("--workbook", required=True, help="Path to the .xlsx recruiting workbook.")
    parser.add_argument(
        "--market",
        default="all",
        choices=sorted(MARKETS) + ["all"],
        help="A specific market slug, or 'all' (default) to update every market's tab.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    workbook_path = Path(args.workbook)

    if not workbook_path.exists():
        raise FileNotFoundError(
            f"Could not find workbook at {workbook_path}. "
            "Pass the correct path with --workbook \"path\\to\\file.xlsx\"."
        )

    print(f"[workbook] {workbook_path}")
    workbook = load_workbook(workbook_path)

    markets_to_run = sorted(MARKETS) if args.market == "all" else [args.market]

    updated_tabs = []
    for market_slug in markets_to_run:
        output_rows = process_market(market_slug)
        tab_name = write_market_tab(workbook, market_slug, output_rows)
        updated_tabs.append(tab_name)
        print(f"[tab] wrote '{tab_name}' ({len(output_rows)} rows)")

    workbook.save(workbook_path)
    print(f"\nSaved. Updated tabs: {', '.join(updated_tabs)}")


if __name__ == "__main__":
    main()
