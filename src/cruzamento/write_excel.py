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
    PERC_FMT   = '0.00%'

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
        "D190":   "D190 - Itens CT-e (EFD Fiscal x EFD Contribuicoes)",
        "A170":   "A170 - Itens NF de Servico ISS (EFD Contribuicoes)",
        "F100":   "F100 - Receitas e Despesas Diversas (EFD Contribuicoes)",
        "ANALISE_OPERACOES":   "Análise Operações ICMS por CFOP (EFD Fiscal)",
        "ANALISE_PRODUTOS":    "Análise de Produtos por Valor Movimentado (EFD Contribuições)",
        "ANALISE_USO_CONSUMO": "Análise Uso e Consumo - Itens sem PIS/COFINS no EFD Contribuições",
        "ANALISE_INSUMOS":     "Análise Insumos - Itens sem PIS/COFINS no EFD Contribuições",
        "ANALISE_REVENDA":     "Análise Revenda - Itens sem PIS/COFINS no EFD Contribuições",
        "ANALISE_ATIVO_IMOB":  "Análise Ativo Imobilizado - Itens sem PIS/COFINS no EFD Contribuições",
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
        img.width  = 338
        img.height = 72
        ws.add_image(img)

        ws["B6"].value = empresa
        ws["B6"].font  = f10_bold

        c7           = ws["B7"]
        _cfops_meta  = fase1_data.get("_CFOPS", {})
        _cfops       = _cfops_meta.get(nome_aba)
        subtitulo    = SUBTITULOS[nome_aba]
        if _cfops:
            subtitulo += " (CFOPs: " + ", ".join(_cfops) + ")"
        c7.value     = subtitulo
        c7.font      = f10_bold_orange
        c7.fill      = fill_white
        c7.alignment = align_left

        if nome_aba != "RESUMO":
            dxf_12 = DifferentialStyle(
                font   = Font(bold=True, color=WHITE),
                fill   = PatternFill(bgColor="FF641E"),
                border = Border(top=Side(style="thin", color="7E131E")),
            )
            ws.conditional_formatting.add(
                "B11:BZ11",
                Rule(type="expression", formula=['LEN(TRIM(B11))>0'],
                     dxf=dxf_12, priority=1),
            )

    # ── Borda laranja na linha 8 estendida até a última coluna ──────
    def _set_orange_border_row8(ws, last_col: int) -> None:
        for col in range(2, last_col + 1):
            ws.cell(8, col).border = border_bottom_orange

    # ── Atribuição de grupos por coluna ──────────────────────────────
    def _assign_grupos(cols: list) -> list:
        chave_cols = {"ITEM_KEY", cd.EM_EFD_C}
        if cd.EXCLUSIVO_EFD_C in cols:
            return ["EFD Contribuicoes"] * len(cols)
        if not chave_cols.intersection(cols):
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

    # ── Autofit de colunas numéricas nas sheets de análise ──────────
    def _autofit_numeric_cols(ws, df: pl.DataFrame, col_offset: int = 2) -> None:
        """
        Ajusta a largura de cada coluna numérica para garantir que o valor
        formatado no padrão contábil fique visível sem truncamento.

        Simula o espaço necessário com f"{max_abs:,.2f}" (separadores de milhar
        e 2 decimais) mais margem para os espaços do formato contábil Excel.
        Considera também o comprimento do header como largura mínima.
        """
        if df.is_empty():
            return
        _NUM = (pdt.Float32, pdt.Float64, pdt.Int8, pdt.Int16,
                pdt.Int32, pdt.Int64, pdt.UInt8, pdt.UInt16,
                pdt.UInt32, pdt.UInt64)
        for j, (col_name, dtype) in enumerate(zip(df.columns, df.dtypes)):
            if not isinstance(dtype, _NUM):
                continue
            col_letter = get_column_letter(col_offset + j)
            try:
                max_abs = df[col_name].drop_nulls().abs().max()
                max_abs = float(max_abs) if max_abs is not None else 0.0
                # Comprimento da string formatada + margem do formato contábil
                formatted_len = len(f"{max_abs:,.2f}") + 4
                header_len    = len(col_name) + 2
                width = max(formatted_len, header_len, 12)
            except Exception:
                width = 15
            cur = ws.column_dimensions[col_letter].width or 0
            if width > cur:
                ws.column_dimensions[col_letter].width = width

    # ── Escrever dados nas abas transacionais ────────────────────────
    def _escrever_aba(sheet_name: str, df: pl.DataFrame, chave: str = "") -> None:
        ws     = wb[sheet_name]
        cols   = list(df.columns)
        n_cols = len(cols)
        if n_cols == 0:
            return
        grupos = _assign_grupos(cols)

        # Colunas numéricas pelo schema do Polars
        _NUMERIC = (pdt.Float32, pdt.Float64, pdt.Int8, pdt.Int16,
                    pdt.Int32, pdt.Int64, pdt.UInt8, pdt.UInt16,
                    pdt.UInt32, pdt.UInt64)

        _set_orange_border_row8(ws, 1 + n_cols)

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

        perc_cols = {j + 2 for j, name in enumerate(cols) if name == "PERC"}

        is_analise = (chave or sheet_name).startswith("ANALISE_")

        # Linha 12+: dados via append, com number_format aplicado por célula nas colunas numéricas
        # Contador explícito evita chamar ws.max_row (O(n) em certas versões do openpyxl) a cada linha.
        _row_idx = 11  # headers estão na linha 11; dados começam na 12
        for row_data in df.iter_rows(named=False):
            ws.append([None] + list(row_data))
            _row_idx += 1
            if numeric_cols:
                for col_idx in numeric_cols:
                    fmt = PERC_FMT if col_idx in perc_cols else NUMBER_FMT
                    ws.cell(_row_idx, col_idx).number_format = fmt

        # Linha de total nas sheets de análise: mesmo estilo do cabeçalho de grupo
        if is_analise and not df.is_empty():
            total_row = _row_idx
            for col_idx in range(2, 2 + n_cols):
                cell      = ws.cell(total_row, col_idx)
                cell.fill = fill_orange
                cell.font = f10_bold_white
            # Autofit nas colunas numéricas para garantir visibilidade dos valores
            _autofit_numeric_cols(ws, df)

    # ── Escrever duas tabelas lado a lado (ANALISE_OPERACOES / ANALISE_PRODUTOS)
    def _escrever_aba_dupla(sheet_name: str, df_ent: pl.DataFrame, df_sai: pl.DataFrame) -> None:
        ws    = wb[sheet_name]
        n_ent = len(df_ent.columns) if not df_ent.is_empty() else 0
        n_sai = len(df_sai.columns) if not df_sai.is_empty() else 0
        sep_col = 2 + n_ent       # coluna separadora (em branco)
        sai_col = sep_col + 1     # início da tabela de saídas

        _set_orange_border_row8(ws, sai_col - 1 + n_sai)

        # Linha 10: labels de seção
        if n_ent:
            ws.merge_cells(start_row=10, start_column=2,
                           end_row=10, end_column=1 + n_ent)
            c = ws.cell(10, 2, "Entradas")
            c.fill = GRUPO_FILLS["EFD ICMS IPI"]
            c.font = f10_bold_white
            c.alignment = align_center
        if n_sai:
            ws.merge_cells(start_row=10, start_column=sai_col,
                           end_row=10, end_column=sai_col - 1 + n_sai)
            c = ws.cell(10, sai_col, "Saídas")
            c.fill = GRUPO_FILLS["EFD Contribuicoes"]
            c.font = f10_bold_white
            c.alignment = align_center

        # Linha 11: headers
        for j, col in enumerate(df_ent.columns if not df_ent.is_empty() else [], start=2):
            c = ws.cell(11, j, col)
            c.font = f11_bold
            c.alignment = align_center
        for j, col in enumerate(df_sai.columns if not df_sai.is_empty() else [], start=sai_col):
            c = ws.cell(11, j, col)
            c.font = f11_bold
            c.alignment = align_center
        if n_ent or n_sai:
            ws.auto_filter.ref = f"B11:{get_column_letter(sai_col - 1 + n_sai)}11"

        _NUMERIC = (pdt.Float32, pdt.Float64, pdt.Int8, pdt.Int16,
                    pdt.Int32, pdt.Int64, pdt.UInt8, pdt.UInt16,
                    pdt.UInt32, pdt.UInt64)

        def _col_fmts(df, offset):
            return {
                offset + j: (PERC_FMT if name == "PERC" else NUMBER_FMT)
                for j, (name, dtype) in enumerate(zip(df.columns, df.dtypes))
                if isinstance(dtype, _NUMERIC)
            }

        ent_fmts = _col_fmts(df_ent, 2)       if not df_ent.is_empty() else {}
        sai_fmts = _col_fmts(df_sai, sai_col) if not df_sai.is_empty() else {}

        ent_rows = list(df_ent.iter_rows(named=False)) if not df_ent.is_empty() else []
        sai_rows = list(df_sai.iter_rows(named=False)) if not df_sai.is_empty() else []
        n_rows   = max(len(ent_rows), len(sai_rows), 0)

        for i in range(n_rows):
            row_num = 12 + i
            if i < len(ent_rows):
                for j, val in enumerate(ent_rows[i], start=2):
                    cell = ws.cell(row_num, j, val)
                    if j in ent_fmts:
                        cell.number_format = ent_fmts[j]
            if i < len(sai_rows):
                for j, val in enumerate(sai_rows[i], start=sai_col):
                    cell = ws.cell(row_num, j, val)
                    if j in sai_fmts:
                        cell.number_format = sai_fmts[j]

        # Linha de total de cada lado (última linha)
        if ent_rows:
            tr = 12 + len(ent_rows) - 1
            for col_idx in range(2, 2 + n_ent):
                ws.cell(tr, col_idx).fill = fill_orange
                ws.cell(tr, col_idx).font = f10_bold_white
        if sai_rows:
            tr = 12 + len(sai_rows) - 1
            for col_idx in range(sai_col, sai_col + n_sai):
                ws.cell(tr, col_idx).fill = fill_orange
                ws.cell(tr, col_idx).font = f10_bold_white

        # Autofit nas colunas numéricas de cada lado
        if not df_ent.is_empty():
            _autofit_numeric_cols(ws, df_ent, 2)
        if not df_sai.is_empty():
            _autofit_numeric_cols(ws, df_sai, sai_col)

    # ── Escrever aba RESUMO ──────────────────────────────────────────
    def _write_resumo(ws) -> None:
        ri = resumo_info or {}
        _set_orange_border_row8(ws, 9)

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

        current = 10

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

    # Ordem e nomes de exibição das abas (chave interna → nome da tab Excel)
    _SHEET_ORDER = [
        "C170", "D190", "A170", "F100",
        "ANALISE_USO_CONSUMO", "ANALISE_ATIVO_IMOB",
        "ANALISE_INSUMOS",     "ANALISE_REVENDA",
        "ANALISE_OPERACOES",   "ANALISE_PRODUTOS",
    ]
    _SHEET_NAMES = {
        "C170":               "C170",
        "D190":               "D190",
        "A170":               "A170",
        "F100":               "F100",
        "ANALISE_USO_CONSUMO": "Análise Uso e Consumo",
        "ANALISE_ATIVO_IMOB":  "Análise Ativo Imobilizado",
        "ANALISE_INSUMOS":     "Análise Insumos",
        "ANALISE_REVENDA":     "Análise Revenda",
        "ANALISE_OPERACOES":   "Análise Operações",
        "ANALISE_PRODUTOS":    "Análise Produtos",
    }
    _SHEETS_DUPLA = {"ANALISE_OPERACOES", "ANALISE_PRODUTOS"}

    for nome in _SHEET_ORDER:
        tab_name = _SHEET_NAMES[nome]
        data     = fase1_data.get(nome)
        is_dupla = nome in _SHEETS_DUPLA
        if is_dupla:
            df_ent = (data or {}).get("ent", pl.DataFrame())
            df_sai = (data or {}).get("sai", pl.DataFrame())
            if df_ent.is_empty() and df_sai.is_empty():
                continue
            _setup_sheet(wb.create_sheet(tab_name), nome)
            _escrever_aba_dupla(tab_name, df_ent, df_sai)
        else:
            has_data = data is not None and not data.is_empty()
            if nome.startswith("ANALISE_") and not has_data:
                continue
            _setup_sheet(wb.create_sheet(tab_name), nome)
            _escrever_aba(tab_name, data if data is not None else pl.DataFrame(), nome)

    # ── RESUMO ───────────────────────────────────────────────────────
    last_content_row = _write_resumo(ws_resumo)

    sheets_com_dados = []
    for k in _SHEET_ORDER:
        d = fase1_data.get(k)
        if k in _SHEETS_DUPLA:
            ent = (d or {}).get("ent", pl.DataFrame())
            sai = (d or {}).get("sai", pl.DataFrame())
            if not ent.is_empty() or not sai.is_empty():
                sheets_com_dados.append(k)
        else:
            if d is not None and not d.is_empty():
                sheets_com_dados.append(k)
    for i, sname in enumerate(sheets_com_dados, start=last_content_row):
        tab_name       = _SHEET_NAMES[sname]
        cell           = ws_resumo.cell(i, 2, tab_name)
        cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'{tab_name}'!A1")
        cell.font      = f11_link

    wb.save(filename)
    self.logger.info(f"[OPORTUNIDADES] Output salvo: {filename}")


def excel_arquivos_recebidos(
    self, empresa: str, arquivos_info: pl.DataFrame, projeto: str
) -> None:
    """
    Gera arquivo Excel separado com relatorio de arquivos recebidos:
    processados e nao processados, com layout Apter padrao.
    """
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    directory     = os.path.dirname(os.path.abspath(__file__))
    output_folder = self.global_params["output"]
    logo_path     = os.path.join(directory, "assets", "templates", "apter_logo.png")

    filename = (
        output_folder + "\\"
        + "Apter_Oportunidades_" + projeto + "_Relatório_Processamento_"
        + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx"
    )

    ORANGE   = "FFFF641E"
    DARK_RED = "FF7E131E"
    WHITE    = "FFFFFFFF"
    GREEN_OK = "FF70AD47"
    RED_WARN = "FFC00000"

    f10_bold        = Font(name="Calibri", size=10, bold=True)
    f10_bold_orange = Font(name="Calibri", size=10, bold=True, color=ORANGE)
    f11_bold_white  = Font(name="Calibri", size=11, bold=True, color=WHITE)

    fill_white  = PatternFill("solid", fgColor=WHITE)
    fill_orange = PatternFill("solid", fgColor=ORANGE)

    align_left   = Alignment(horizontal="left")
    align_center = Alignment(horizontal="center")
    border_bottom_orange = Border(bottom=Side(style="thin", color=ORANGE))

    wb = Workbook()
    ws = wb.active
    ws.title = "Arquivos Recebidos"

    ws.sheet_view.showGridLines   = False
    ws.sheet_view.zoomScale       = 80
    ws.sheet_view.zoomScaleNormal = 80
    ws.column_dimensions["A"].width = 2.63

    img        = XLImage(logo_path)
    img.anchor = "A1"
    img.width  = 338
    img.height = 72
    ws.add_image(img)

    ws["B6"].value     = empresa
    ws["B6"].font      = f10_bold

    ws["B7"].value     = "Oportunidades - Relatório de Arquivos Recebidos"
    ws["B7"].font      = f10_bold_orange
    ws["B7"].fill      = fill_white
    ws["B7"].alignment = align_left

    # Linha 10: cabecalho das colunas
    headers = [cd.file_name, cd.status, cd.processamento]
    widths  = [60, 40, 18]

    for col in range(2, 2 + len(headers)):
        ws.cell(8, col).border = border_bottom_orange

    for j, (lbl, w) in enumerate(zip(headers, widths), start=2):
        c           = ws.cell(10, j, lbl)
        c.font      = f11_bold_white
        c.fill      = fill_orange
        c.alignment = align_center
        ws.column_dimensions[get_column_letter(j)].width = w

    ws.auto_filter.ref = f"B10:{get_column_letter(1 + len(headers))}10"

    # Dados a partir da linha 11
    if not arquivos_info.is_empty():
        for i, row in enumerate(arquivos_info.iter_rows(named=True), start=11):
            fname = row.get(cd.file_name, "") or ""
            tipo  = row.get(cd.status, "") or ""
            proc  = row.get(cd.processamento, "") or ""
            is_ok = proc == "Processado"
            ws.cell(i, 2, fname).alignment = align_left
            ws.cell(i, 3, tipo).alignment  = align_left
            c_proc           = ws.cell(i, 4, proc)
            c_proc.font      = Font(
                name="Calibri", size=10, bold=True,
                color=GREEN_OK if is_ok else RED_WARN,
            )
            c_proc.alignment = align_center
    else:
        c           = ws.cell(11, 2, "Nenhum arquivo identificado")
        c.font      = f10_bold
        c.alignment = align_left

    wb.save(filename)
    self.logger.info(f"[OPORTUNIDADES] Relatorio de arquivos salvo: {filename}")
