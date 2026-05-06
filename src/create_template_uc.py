"""
create_template_uc.py
─────────────────────
One-shot script to generate the formatted Taxverse template for
the Use & Consumption credit analysis module.

Run from the project root:
    python src/create_template_uc.py
"""

import os
import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# ── Taxverse palette ──────────────────────────────────────────────────────────
NAVY        = "1F3864"
NAVY_LIGHT  = "2E5797"
GOLD        = "BF8F00"
GOLD_LIGHT  = "F4CF5C"
LIGHT_GRAY  = "F2F2F2"
MID_GRAY    = "D6DCE4"
WHITE       = "FFFFFF"
GREEN_ELEG  = "E2EFDA"
GREEN_H     = "375623"
YELLOW_REV  = "FFEB9C"
YELLOW_H    = "7D6608"
RED_NAO     = "FFC7CE"
RED_H       = "9C0006"

# Fonts
FONT_BANNER    = Font(name="Calibri", bold=True, size=18, color=WHITE)
FONT_TAB_TITLE = Font(name="Calibri", bold=True, size=13, color=WHITE)
FONT_HEADER    = Font(name="Calibri", bold=True, size=10, color=WHITE)
FONT_LABEL     = Font(name="Calibri", bold=True, size=11, color=NAVY)
FONT_DATA      = Font(name="Calibri", size=11)
FONT_SMALL     = Font(name="Calibri", size=9, color="595959")

# Fills
FILL_NAVY      = PatternFill(fill_type="solid", fgColor=NAVY)
FILL_NAVY_LT   = PatternFill(fill_type="solid", fgColor=NAVY_LIGHT)
FILL_GOLD      = PatternFill(fill_type="solid", fgColor=GOLD)
FILL_GRAY      = PatternFill(fill_type="solid", fgColor=LIGHT_GRAY)
FILL_MID_GRAY  = PatternFill(fill_type="solid", fgColor=MID_GRAY)
FILL_GREEN     = PatternFill(fill_type="solid", fgColor=GREEN_ELEG)
FILL_YELLOW    = PatternFill(fill_type="solid", fgColor=YELLOW_REV)
FILL_RED       = PatternFill(fill_type="solid", fgColor=RED_NAO)
FILL_WHITE     = PatternFill(fill_type="solid", fgColor=WHITE)

# Border helpers
THIN  = Side(style="thin",   color="BFBFBF")
THICK = Side(style="medium", color=NAVY)
BORDER_ALL   = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BORDER_THICK = Border(left=THICK, right=THICK, top=THICK, bottom=THICK)

ALIGN_CC  = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LC  = Alignment(horizontal="left",   vertical="center")
ALIGN_RC  = Alignment(horizontal="right",  vertical="center")


def _style_cell(cell, font=None, fill=None, alignment=None, border=None):
    if font:      cell.font      = font
    if fill:      cell.fill      = fill
    if alignment: cell.alignment = alignment
    if border:    cell.border    = border


def _set_col_widths(ws: Worksheet, widths: dict[str, float]):
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _banner_row(ws: Worksheet, merge: str, text: str, row_h: float = 32):
    ws.merge_cells(merge)
    cell = ws[merge.split(":")[0]]
    cell.value     = text
    cell.font      = FONT_BANNER
    cell.fill      = FILL_NAVY
    cell.alignment = ALIGN_CC
    row_num = int("".join(filter(str.isdigit, merge.split(":")[0])))
    ws.row_dimensions[row_num].height = row_h


def _section_title(ws: Worksheet, merge: str, text: str, fill=None, font=None, row_h=20):
    ws.merge_cells(merge)
    cell = ws[merge.split(":")[0]]
    cell.value     = text
    cell.font      = font or FONT_TAB_TITLE
    cell.fill      = fill or FILL_NAVY_LT
    cell.alignment = ALIGN_CC
    row_num = int("".join(filter(str.isdigit, merge.split(":")[0])))
    ws.row_dimensions[row_num].height = row_h


def _label_data(ws: Worksheet, label_coord: str, label_val: str,
                data_coord: str, data_val: str = ""):
    lc = ws[label_coord]
    lc.value, lc.font, lc.alignment = label_val, FONT_LABEL, ALIGN_LC
    dc = ws[data_coord]
    dc.value, dc.font, dc.border, dc.alignment = data_val, FONT_DATA, Border(bottom=THIN), ALIGN_LC


def _header_row(ws: Worksheet, row: int, columns: list[str], start_col: int = 2):
    ws.row_dimensions[row].height = 32
    for i, col_name in enumerate(columns, start=start_col):
        cell = ws.cell(row, i, col_name)
        cell.font      = FONT_HEADER
        cell.fill      = FILL_NAVY
        cell.alignment = ALIGN_CC
        cell.border    = BORDER_ALL
        ws.column_dimensions[get_column_letter(i)].width = max(14, min(len(col_name) + 4, 40))


def _legend_row(ws: Worksheet, row: int, items: list[tuple], start_col: int = 2):
    """Writes a horizontal colour legend."""
    col = start_col
    for fill, label in items:
        cell = ws.cell(row, col)
        cell.fill      = fill
        cell.border    = BORDER_ALL
        cell.alignment = ALIGN_CC
        cell.value     = ""
        col += 1
        lc = ws.cell(row, col)
        lc.value, lc.font, lc.alignment = label, FONT_SMALL, ALIGN_LC
        col += 2


# ─── Build ÍNDICE sheet ───────────────────────────────────────────────────────

def build_indice(ws: Worksheet):
    ws.sheet_view.showGridLines = False
    ws.title = "ÍNDICE"

    _banner_row(ws, "B2:L4", "APTER CONSULTORIA TRIBUTÁRIA", row_h=35)
    _section_title(ws, "B5:L5", "Análise de Elegibilidade de Crédito — Uso & Consumo",
                   fill=FILL_GOLD, font=Font(name="Calibri", bold=True, size=12, color=NAVY))

    ws.row_dimensions[5].height = 24

    data_info = [
        ("B7", "Empresa:",           "D7"),
        ("B8", "CNPJ:",              "D8"),
        ("B9", "Regime Tributário:", "D9"),
        ("B10", "Período Início:",   "D10"),
        ("B11", "Período Fim:",      "D11"),
    ]
    for label_c, label_v, data_c in data_info:
        _label_data(ws, label_c, label_v, data_c)
        ws.merge_cells(f"{data_c}:{data_c[0]}{data_c[1:]}".replace("D", "L"))

    ws.row_dimensions[7].height  = 18
    ws.row_dimensions[8].height  = 18
    ws.row_dimensions[9].height  = 18
    ws.row_dimensions[10].height = 18
    ws.row_dimensions[11].height = 18

    # Nav links note
    nav = ws["B13"]
    nav.value     = "Navegação: → RESUMO   → DETALHES   → ORFAOS"
    nav.font      = Font(name="Calibri", italic=True, size=10, color="595959")
    nav.alignment = ALIGN_LC

    _set_col_widths(ws, {"A": 3, "B": 22, "C": 3, "D": 42, "L": 3})


# ─── Build RESUMO sheet ───────────────────────────────────────────────────────
RESUMO_COLS = [
    "EMPRESA", "CNPJ", "REGIME_TRIBUTARIO",
    "PERIODO_INI", "PERIODO_FIM",
    "TOTAL_NFS_ANALISADAS", "TOTAL_ITENS_CRUZADOS",
    "TOTAL_ITENS_USO_CONSUMO",
    "TOTAL_ELEGIVEL", "TOTAL_REVISAO", "TOTAL_NAO_ELEGIVEL",
    "TOTAL_ORFAOS",
    "VL_CREDITO_PIS", "VL_CREDITO_COFINS", "VL_CREDITO_TOTAL",
]

def build_resumo(ws: Worksheet):
    ws.sheet_view.showGridLines = False
    _section_title(ws, "B2:R3", "RESUMO DA ANÁLISE — USO & CONSUMO")
    ws.row_dimensions[2].height = 24
    ws.row_dimensions[3].height = 24

    # Colour legend
    _legend_row(ws, 8, [
        (FILL_GREEN,  "Elegível"),
        (FILL_YELLOW, "Revisão Necessária"),
        (FILL_RED,    "Não Elegível"),
    ], start_col=2)
    ws["B7"].value = "Legenda de Elegibilidade:"
    ws["B7"].font  = FONT_LABEL

    # Headers at row 12
    _header_row(ws, 12, RESUMO_COLS, start_col=2)
    ws["B12"].fill = FILL_NAVY   # first header (over-write for emphasis)

    # Metric labels (vertical layout alternative rows 12+)
    _set_col_widths(ws, {"A": 3, **{get_column_letter(i): 22 for i in range(2, 18)}})


# ─── Build DETALHES sheet ─────────────────────────────────────────────────────
DETALHES_COLS = [
    "CHAVE_NF (JOIN_KEY)", "CHV_NFE", "COD_PART", "RAZAO_SOCIAL",
    "CNPJ_EMIT", "NUM_DOC", "SER", "DT_DOC",
    "CFOP", "DESCR_COMPL",
    "CST_PIS", "CST_COFINS",
    "ALIQ_PIS (%)", "ALIQ_COFINS (%)",
    "VL_ITEM",
    "VL_BC_PIS", "VL_BC_COFINS",
    "ELEGIBILIDADE",
    "VL_CREDITO_PIS", "VL_CREDITO_COFINS", "VL_CREDITO_TOTAL",
    "OBSERVACOES",
]

def build_detalhes(ws: Worksheet):
    ws.sheet_view.showGridLines = False
    _section_title(ws, "B2:Z3", "DETALHES — ITENS DE USO & CONSUMO ANALISADOS")

    # Legend
    ws["B5"].value, ws["B5"].font = "Legenda:", FONT_LABEL
    _legend_row(ws, 5, [
        (FILL_GREEN,  "Elegível — crédito calculado"),
        (FILL_YELLOW, "Revisão — verificar escrituração"),
        (FILL_RED,    "Não Elegível"),
    ], start_col=4)
    ws.row_dimensions[5].height = 18

    # Instruction
    ws["B7"].value = (
        "Ordenação: Elegível → Revisão → Não Elegível | "
        "dentro de cada grupo: maior valor de crédito primeiro."
    )
    ws["B7"].font      = Font(name="Calibri", italic=True, size=9, color="595959")
    ws["B7"].alignment = ALIGN_LC
    ws.merge_cells("B7:Z7")

    # Headers
    _header_row(ws, 12, DETALHES_COLS, start_col=2)
    ws.freeze_panes = "B13"

    # Sample eligibility colour rows (visual reference only — data overwrites these)
    sample_fills = [FILL_GREEN, FILL_YELLOW, FILL_RED]
    for ri, fill in enumerate(sample_fills, start=13):
        for ci in range(2, len(DETALHES_COLS) + 2):
            ws.cell(ri, ci).fill   = fill
            ws.cell(ri, ci).border = BORDER_ALL

    _set_col_widths(ws, {
        "A": 3,
        "B": 18, "C": 14, "D": 12, "E": 30, "F": 18,
        "G": 12, "H": 6,  "I": 12, "J": 8,  "K": 30,
        "L": 10, "M": 12, "N": 14, "O": 14, "P": 14,
        "Q": 14, "R": 14, "S": 14, "T": 14, "U": 16,
        "V": 16, "W": 40,
    })


# ─── Build ORFAOS sheet ───────────────────────────────────────────────────────
ORFAOS_COLS = [
    "CHAVE_NF", "CHV_NFE", "COD_PART", "NUM_DOC", "SER", "DT_DOC",
    "VL_DOC", "OBRIGACAO_FALTANTE",
]

def build_orfaos(ws: Worksheet):
    ws.sheet_view.showGridLines = False
    _section_title(ws, "B2:M3", "ÓRFÃOS — DOCUMENTOS SEM CORRESPONDÊNCIA ENTRE AS EFDs",
                   fill=PatternFill(fill_type="solid", fgColor="4472C4"))

    ws["B5"].value = (
        "Registros aqui presentes indicam inconsistência na escrituração do cliente: "
        "o documento existe em uma EFD mas não foi localizado na outra."
    )
    ws["B5"].font      = Font(name="Calibri", italic=True, size=10, color="595959")
    ws["B5"].alignment = ALIGN_LC
    ws.merge_cells("B5:M5")

    legend_items = [
        (PatternFill(fill_type="solid", fgColor="9DC3E6"), "Apenas EFD ICMS IPI"),
        (PatternFill(fill_type="solid", fgColor="FFD966"), "Apenas EFD Contribuições"),
    ]
    ws["B7"].value, ws["B7"].font = "Legenda:", FONT_LABEL
    _legend_row(ws, 7, legend_items, start_col=4)

    _header_row(ws, 12, ORFAOS_COLS, start_col=2)
    ws.freeze_panes = "B13"

    _set_col_widths(ws, {
        "A": 3, "B": 18, "C": 14, "D": 12,
        "E": 12, "F": 6, "G": 12, "H": 14,
        "I": 30,
    })


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets", "templates", "Template_Uso_Consumo.xlsx"
    )

    wb = openpyxl.Workbook()

    # Build sheets in order
    ws_idx = wb.active
    build_indice(ws_idx)

    ws_res = wb.create_sheet("RESUMO")
    build_resumo(ws_res)

    ws_det = wb.create_sheet("DETALHES")
    build_detalhes(ws_det)

    ws_orf = wb.create_sheet("ORFAOS")
    build_orfaos(ws_orf)

    wb.save(out_path)
    print(f"✅  Template salvo em: {out_path}")


if __name__ == "__main__":
    main()
