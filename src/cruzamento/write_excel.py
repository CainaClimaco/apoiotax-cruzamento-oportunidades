from datetime import datetime
import datatricks.io.excel_handler as eh
import cruzamento.cruzamento_definition as cd
import os
import polars as pl
import polars.datatypes as pdt


def excel_escrituracao(self, empresa, escrituracao, analise, projeto):
    """
    Description:
        Writes the output files generated from the analysis.
    Parameters:
        self:
        empresa: Company name.
        escrituracao: Dataframe with the data to be written.
        analise: Dataframe with the information about the files that could not be processed.
        projeto: Project name.
    """
    directory = os.path.dirname(os.path.abspath(__file__))
    output_folder = self.global_params["output"]

    cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_Check SPED x XML_v5.xlsx')
    wb = eh.open_template(cruzamentos_file)
    company = pl.DataFrame([empresa])

    eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B7', write_header=False, sheet_name="Índice")
    eh.dump_data_to_sheet(excel_thing=wb, data=escrituracao, starting_cell='B11', write_header=True, sheet_name="SPED x XML")
    eh.dump_data_to_sheet(excel_thing=wb, data=analise, starting_cell='B11', write_header=True, sheet_name="ARQUIVOS_PARA_ANALISE")
    wb.save(output_folder + "\\" + "1. Apter_" + projeto +   " - Check SPED x XML_" +  datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


def excel_receita(self, empresa, Contribuicoes, Fiscal, Notas, NFE, nConsiderada, nProcessado, Anual, Trimestral, Consolidado, Analitico, projeto):
    """
    Description:
        Writes the output files generated from the analysis
    Parameters:
        self:
        empresa: Company name.
        Contribuicoes: Processed SPED Contribuições data.
        Fiscal: Processed SPED Fiscal data.
        Notas: DataFrame containing the data summary.
        NFE: Processed NFe data.
        nConsiderada: DataFrame with datas that were not considered.     
        nProcessado: DataFrame with datas that could not be processed.
        Anual: Annual summary.
        Trimestral: Quarterly summary.
        Consolidado: Dataframe with the consolidated view.
        Analitico: Dataframe with the analytic view.
        projeto: Project name.
    """
    
    directory = os.path.dirname(os.path.abspath(__file__))
    output_folder = self.global_params["output"]

    if Analitico.height > 0:
        anos = Analitico.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            analitico = Analitico.filter(pl.col(cd.ANO) == ano)
            analitico = analitico.drop(cd.ANO)
            analitico = analitico.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))

            anual = Anual.filter(pl.col(cd.ANO) == ano)

            trimestral = Trimestral.filter(pl.col(cd.ANO) == ano)
            trimestral = trimestral.drop(cd.linha)

            consolidado = Consolidado.filter(pl.col(cd.ANO) == ano)
            consolidado = consolidado.drop(cd.ANO, cd.linha)
            consolidado = consolidado.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))

            cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_ANALITICO.xlsx')
            wb = eh.open_template(cruzamentos_file)
            company = pl.DataFrame([empresa])

            eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
            eh.dump_data_to_sheet(excel_thing=wb, data=analitico, starting_cell='B12', write_header=False, sheet_name="CONFRONTO - ANALITICO")
            eh.dump_data_to_sheet(excel_thing=wb, data=anual, starting_cell='B12', write_header=False, sheet_name="CONFRONTO - ANUAL")
            eh.dump_data_to_sheet(excel_thing=wb, data=trimestral, starting_cell='B12', write_header=False, sheet_name="CONFRONTO - TRIMESTRAL")
            eh.dump_data_to_sheet(excel_thing=wb, data=consolidado, starting_cell='B12', write_header=False, sheet_name="CONFRONTO - CONSOLIDAÇÃO")
            wb.save(output_folder + "\\" + "1. Apter_CruzamentoSPED_" + str(ano) + "_"  + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if Fiscal.height > 0:
        anos = Fiscal.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            Fisc = Fiscal.filter(pl.col(cd.ANO) == ano)
            Fisc = Fisc.drop(cd.ANO)
            Fisc = Fisc.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))

            cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_EFDFISCAL.xlsx')
            wb = eh.open_template(cruzamentos_file)
            company = pl.DataFrame([empresa])

            eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
            eh.dump_data_to_sheet(excel_thing=wb, data=Fisc, starting_cell='B12', write_header=False, sheet_name="EFD ICMS IPI")
            wb.save(output_folder + "\\" + "2. Apter_EFD_Fiscal_" + str(ano) + "_"  + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if Contribuicoes.height > 0:
        anos = Contribuicoes.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            contrib = Contribuicoes.filter(pl.col(cd.ANO) == ano)
            contrib = contrib.drop(cd.ANO)
            contrib = contrib.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))

            cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_EFDCONTRIBUICOES.xlsx')
            wb = eh.open_template(cruzamentos_file)
            company = pl.DataFrame([empresa])

            eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
            eh.dump_data_to_sheet(excel_thing=wb, data=contrib, starting_cell='B12', write_header=False, sheet_name="EFD CONTRIBUICOES")
            wb.save(output_folder + "\\" + "3. Apter_EFD_Contribuições_" + str(ano) + "_" + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    
    
    if Notas.height > 0:
        anos = Notas.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            notas = Notas.filter(pl.col(cd.ANO) == ano)
            notas = notas.drop(cd.ANO)
            notas = notas.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))

            cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_NOTAS.xlsx')
            wb = eh.open_template(cruzamentos_file)
            company = pl.DataFrame([empresa])

            eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B6', write_header=False, sheet_name="ÍNDICE")
            eh.dump_data_to_sheet(excel_thing=wb, data=notas, starting_cell='B12', write_header=False, sheet_name="NOTAS")
            wb.save(output_folder + "\\" + "4. Apter_Notas_" + str(ano) + "_" + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if NFE.height > 0:
        anos = NFE.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            nf = NFE.filter(pl.col(cd.ANO) == ano)
            nf = nf.drop(cd.ANO)
            nf = nf.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))

            cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_XML.xlsx')
            wb = eh.open_template(cruzamentos_file)
            company = pl.DataFrame([empresa])

            eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B6', write_header=False, sheet_name="ÍNDICE")
            eh.dump_data_to_sheet(excel_thing=wb, data=nf, starting_cell='B12', write_header=False, sheet_name="XML")
            wb.save(output_folder + "\\" + "5. Apter_XML_" + str(ano) + "_" + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if nConsiderada is not None and nConsiderada.height > 0:
        anos = nConsiderada.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            nConsid = nConsiderada.filter(pl.col(cd.ANO) == ano)
            nConsid = nConsid.drop(cd.ANO)
            nConsid = nConsid.with_columns(pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y"))
            
        cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_XML_N_CONSIDERADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B6', write_header=False, sheet_name="ÍNDICE")
        eh.dump_data_to_sheet(excel_thing=wb, data=nConsid, starting_cell='B12', write_header=False, sheet_name="XML - N_CONSIDERADOS")
        wb.save(output_folder + "\\" + "6. Apter_Não_Considerados - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    

    if nProcessado is not None and nProcessado.height > 0:
        cruzamentos_file = os.path.join(directory, 'assets', 'templates', 'Template_N_PROCESSADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B6', write_header=False, sheet_name="ÍNDICE")
        eh.dump_data_to_sheet(excel_thing=wb, data=nProcessado, starting_cell='B12', write_header=False, sheet_name="ARQUIVOS_PARA_ANALISE")
        wb.save(output_folder + "\\" + "7. Apter_Não_Processados - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    

def excel_oportunidades(self, empresa, fase1_data: dict, projeto: str, resumo_info: dict | None = None) -> None:
    """
    Gera o workbook da FASE 1 de forma totalmente programatica.
    Reproduz o layout Apter: logo, sem gridlines, zoom 80%, formatacao
    condicional nas linhas 9 e 11, headers laranja, bordas, filtro e
    formato numerico contabil brasileiro.
    """
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.formatting.rule import Rule
    from openpyxl.styles.differential import DifferentialStyle
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.hyperlink import Hyperlink

    directory     = os.path.dirname(os.path.abspath(__file__))
    output_folder = self.global_params["output"]
    logo_path     = os.path.join(directory, "assets", "templates", "apter_logo.png")

    filename = (
        output_folder + "\\"
        + "Apter_Oportunidades_" + projeto + "_"
        + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx"
    )

    # ── Constantes de estilo ─────────────────────────────────────────
    ORANGE     = "FFFF641E"
    DARK_RED   = "FF7E131E"
    WHITE      = "FFFFFFFF"
    LINK_BLUE  = "FF0070C0"
    NAVY       = "FF2F5597"
    DARK_GREEN = "FF375623"
    GREEN_OK   = "FF70AD47"
    RED_WARN   = "FFC00000"
    NUMBER_FMT = '_(* #,##0.00_);_(* (#,##0.00);_(* "-"_);@_)'

    f10_bold        = Font(name="Calibri", size=10, bold=True)
    f10_bold_white  = Font(name="Calibri", size=10, bold=True, color=WHITE)
    f10_bold_orange = Font(name="Calibri", size=10, bold=True, color=ORANGE)
    f11_bold        = Font(name="Calibri", size=11, bold=True)
    f11_bold_white  = Font(name="Calibri", size=11, bold=True, color=WHITE)
    f11_link        = Font(name="Calibri", size=11, underline="single", color=LINK_BLUE)

    fill_white  = PatternFill("solid", fgColor=WHITE)
    fill_orange = PatternFill("solid", fgColor=ORANGE)

    DS_RED   = "FF83181B"
    DS_AMBER = "FFF39200"
    DS_GRAY  = "FF575756"

    GRUPO_FILLS = {
        "EFD ICMS IPI":      PatternFill("solid", fgColor=DS_RED),
        "CHAVE":             PatternFill("solid", fgColor=DS_AMBER),
        "EFD Contribuicoes": PatternFill("solid", fgColor=DS_GRAY),
    }
    GRUPO_LABELS = {
        "EFD ICMS IPI":      "EFD ICMS IPI",
        "CHAVE":             "CHAVE",
        "EFD Contribuicoes": "EFD Contribuições",
    }

    align_left   = Alignment(horizontal="left")
    align_center = Alignment(horizontal="center")

    border_bottom_orange = Border(bottom=Side(style="thin", color=ORANGE))

    SUBTITULOS = {
        "RESUMO": "Oportunidades - Resumo",
        "C170":   "C170 - Itens NF-e (EFD Fiscal x EFD Contribuicoes)",
        "D190":   "D190 - CT-e Itens (EFD Fiscal x EFD Contribuicoes)",
    }

    # ── Setup de cada aba ────────────────────────────────────────────
    def _setup_sheet(ws, nome_aba: str) -> None:
        ws.sheet_view.showGridLines   = False
        ws.sheet_view.zoomScale       = 80
        ws.sheet_view.zoomScaleNormal = 80
        ws.column_dimensions["A"].width = 2.63
        ws.column_dimensions["B"].width = 22

        img        = XLImage(logo_path)
        img.anchor = "A1"
        img.width  = 255
        img.height = 52
        ws.add_image(img)

        ws["B7"].value = empresa
        ws["B7"].font  = f10_bold

        c8           = ws["B8"]
        c8.value     = SUBTITULOS[nome_aba]
        c8.font      = f10_bold_orange
        c8.fill      = fill_white
        c8.alignment = align_left

        ws["B9"].border = border_bottom_orange

        if nome_aba != "RESUMO":
            dxf_11 = DifferentialStyle(
                font   = Font(bold=True, color=WHITE),
                fill   = PatternFill(bgColor="FF641E"),
                border = Border(top=Side(style="thin", color="7E131E")),
            )
            ws.conditional_formatting.add(
                "B11:BZ11",
                Rule(type="expression", formula=['LEN(TRIM(B11))>0'],
                     dxf=dxf_11, priority=1),
            )

    # ── Atribuição de grupos por coluna ──────────────────────────────
    def _assign_grupos(cols: list) -> list:
        chave_cols = {"ITEM_KEY", cd.EM_EFD_C}
        if cd.EXCLUSIVO_EFD_C in cols:
            return ["EFD Contribuicoes"] * len(cols)
        state  = "EFD ICMS IPI"
        grupos = []
        for col in cols:
            if col in chave_cols:
                state = "CHAVE"
            elif state == "CHAVE":
                state = "EFD Contribuicoes"
            grupos.append(state)
        return grupos

    # ── Escrever dados nas abas transacionais ────────────────────────
    def _escrever_aba(sheet_name: str, df: pl.DataFrame) -> None:
        ws     = wb[sheet_name]
        cols   = list(df.columns)
        n_cols = len(cols)
        grupos = _assign_grupos(cols)

        # Colunas numéricas pelo schema do Polars
        _NUMERIC = (pdt.Float32, pdt.Float64, pdt.Int8, pdt.Int16,
                    pdt.Int32, pdt.Int64, pdt.UInt8, pdt.UInt16,
                    pdt.UInt32, pdt.UInt64)

        # Linha 10: labels de grupo com merge
        i = 0
        while i < len(grupos):
            grp = grupos[i]
            j   = i
            while j < len(grupos) and grupos[j] == grp:
                j += 1
            col_start = i + 2
            col_end   = j - 1 + 2
            if col_start < col_end:
                ws.merge_cells(
                    start_row=10, start_column=col_start,
                    end_row=10,   end_column=col_end,
                )
            cell           = ws.cell(10, col_start, GRUPO_LABELS[grp])
            cell.fill      = GRUPO_FILLS[grp]
            cell.font      = f10_bold_white
            cell.alignment = align_center
            i = j

        # Linha 11: headers
        for j, col in enumerate(cols, start=2):
            cell           = ws.cell(11, j, col)
            cell.font      = f11_bold
            cell.alignment = align_center
        ws.auto_filter.ref = f"B11:{get_column_letter(1 + n_cols)}11"

        numeric_cols = {j + 2 for j, dtype in enumerate(df.dtypes) if isinstance(dtype, _NUMERIC)}

        # Linha 12+: dados via append, com number_format aplicado por célula nas colunas numéricas
        for row_data in df.iter_rows(named=False):
            ws.append([None] + list(row_data))
            if numeric_cols:
                row_idx = ws.max_row
                for col_idx in numeric_cols:
                    ws.cell(row_idx, col_idx).number_format = NUMBER_FMT

    # ── Escrever aba RESUMO ──────────────────────────────────────────
    def _write_resumo(ws) -> None:
        ri = resumo_info or {}

        def _sec(row: int, label: str) -> None:
            c           = ws.cell(row, 2, label)
            c.font      = f11_bold_white
            c.fill      = fill_orange
            c.alignment = align_left
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9)

        def _header_row(row: int, labels: list[str]) -> None:
            for j, lbl in enumerate(labels, start=2):
                c           = ws.cell(row, j, lbl)
                c.font      = f11_bold_white
                c.fill      = PatternFill("solid", fgColor=DARK_RED)
                c.alignment = align_center

        def _status_cell(row: int, col: int, ok: bool) -> None:
            c      = ws.cell(row, col, "OK" if ok else "ATENÇÃO")
            c.font = Font(name="Calibri", size=10, bold=True,
                          color=GREEN_OK if ok else RED_WARN)

        def _presence_cell(row: int, col: int, present: bool) -> None:
            c      = ws.cell(row, col, "Sim" if present else "Não")
            c.font = Font(name="Calibri", size=10, bold=True,
                          color=GREEN_OK if present else RED_WARN)
            c.alignment = align_center

        current = 11

        raizes_f = ri.get("raizes_f", [])
        raizes_c = ri.get("raizes_c", [])
        raiz_ok  = ri.get("raiz_ok", True)

        # ── Identificação ────────────────────────────────────────────
        _sec(current, "IDENTIFICAÇÃO"); current += 1
        _header_row(current, ["Campo", "EFD Fiscal", "EFD Contribuições", "Status"]); current += 1

        rows_id = [
            ("Empresa",          ri.get("empresa", ""),                     ri.get("empresa", ""),                     None),
            ("Versão SPED",      ri.get("versao_f") or "N/A",               ri.get("versao_c") or "N/A",               None),
            ("Raiz CNPJ",        ", ".join(raizes_f) or "N/A",              ", ".join(raizes_c) or "N/A",              raiz_ok),
            ("Estabelecimentos", ", ".join(ri.get("cnpjs_f", [])) or "N/A", ", ".join(ri.get("cnpjs_c", [])) or "N/A", None),
        ]
        for label, val_f, val_c, status_ok in rows_id:
            ws.cell(current, 2, label).font           = f10_bold
            ws.cell(current, 2).alignment             = align_left
            ws.cell(current, 3, str(val_f)).alignment = align_left
            ws.cell(current, 4, str(val_c)).alignment = align_left
            if status_ok is not None:
                _status_cell(current, 5, status_ok)
            current += 1

        current += 1
        # ── Cobertura por período ─────────────────────────────────────
        _sec(current, "COBERTURA"); current += 1
        _header_row(current, [
            "Período", "EFD Fiscal", "EFD Contribuições", "Coincidente",
            "Itens EFD Fiscal", "Itens EFD Contribuições",
        ]); current += 1

        cobertura = ri.get("cobertura", {})
        contagens = ri.get("contagens", {})
        for periodo, pres in sorted(cobertura.items()):
            tem_f = pres.get("f", False)
            tem_c = pres.get("c", False)
            cnt   = contagens.get(periodo, {})
            ws.cell(current, 2, periodo).alignment = align_center
            _presence_cell(current, 3, tem_f)
            _presence_cell(current, 4, tem_c)
            _status_cell(current, 5, tem_f and tem_c)
            ws.cell(current, 6, cnt.get("n_f", "")).alignment = align_center
            ws.cell(current, 7, cnt.get("n_c", "")).alignment = align_center
            current += 1

        current += 1
        # ── Abas disponíveis ─────────────────────────────────────────
        _sec(current, "ABAS DISPONÍVEIS"); current += 1
        return current

    # ── Criar workbook ───────────────────────────────────────────────
    wb              = Workbook()
    ws_resumo       = wb.active
    ws_resumo.title = "RESUMO"
    _setup_sheet(ws_resumo, "RESUMO")

    for nome in ["C170", "D190"]:
        _setup_sheet(wb.create_sheet(nome), nome)

    for key in ["C170", "D190"]:
        df = fase1_data.get(key)
        if df is not None and not df.is_empty():
            _escrever_aba(key, df)

    # ── RESUMO ───────────────────────────────────────────────────────
    last_content_row = _write_resumo(ws_resumo)

    sheets_com_dados = [
        k for k in ["C170", "D190"]
        if (df := fase1_data.get(k)) is not None and not df.is_empty()
    ]
    for i, sname in enumerate(sheets_com_dados, start=last_content_row):
        cell           = ws_resumo.cell(i, 2, sname)
        cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"{sname}!A1")
        cell.font      = f11_link

    wb.save(filename)
    self.logger.info(f"[OPORTUNIDADES] Output salvo: {filename}")
