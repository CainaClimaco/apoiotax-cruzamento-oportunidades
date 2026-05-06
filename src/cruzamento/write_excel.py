from datetime import datetime
import datatricks.io.excel_handler as eh
import cruzamento.cruzamento_definition as cd
import os
import polars as pl


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
    root_directory = os.path.dirname(directory)
    output_folder = self.global_params["output"]
    
    cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_Check SPED x XML_v5.xlsx')
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
    root_directory = os.path.dirname(directory)
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

            cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_ANALITICO.xlsx')
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

            cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_EFDFISCAL.xlsx')
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

            cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_EFDCONTRIBUICOES.xlsx')
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

            cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_NOTAS.xlsx')
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

            cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_XML.xlsx')
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
            
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_XML_N_CONSIDERADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B6', write_header=False, sheet_name="ÍNDICE")
        eh.dump_data_to_sheet(excel_thing=wb, data=nConsid, starting_cell='B12', write_header=False, sheet_name="XML - N_CONSIDERADOS")
        wb.save(output_folder + "\\" + "6. Apter_Não_Considerados - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    

    if nProcessado is not None and nProcessado.height > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_N_PROCESSADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(excel_thing = wb, data= company, starting_cell='B6', write_header=False, sheet_name="ÍNDICE")
        eh.dump_data_to_sheet(excel_thing=wb, data=nProcessado, starting_cell='B12', write_header=False, sheet_name="ARQUIVOS_PARA_ANALISE")
        wb.save(output_folder + "\\" + "7. Apter_Não_Processados - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    

def excel_uso_consumo(self, empresa, cnpj, regime, periodo_ini, periodo_fim,
                      resumo, detalhes, orfaos, projeto):
    """
    Gera o workbook de Uso & Consumo usando o template padrão Taxverse.
    Segue exatamente o mesmo padrão das demais funções de escrita:
      - Empresa em B6 do INDICE (write_header=False)
      - Dados em B12 de cada aba (write_header=False, colunas alinhadas ao header da linha 11)
    """
    directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.dirname(directory)
    output_folder = self.global_params["output"]

    template_path = os.path.join(root_directory, cd.CAMINHO_UC_TEMPLATE.replace('src\\', ''))
    filename = (
        output_folder + "\\"
        + "Apter_UsoeConsumo_"
        + projeto + "_"
        + datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        + ".xlsx"
    )

    wb = eh.open_template(template_path)
    company = pl.DataFrame([empresa])

    # ÍNDICE — nome da empresa em B7 (placeholder 'APTER' no template)
    eh.dump_data_to_sheet(
        excel_thing=wb, data=company,
        starting_cell='B7', write_header=False, sheet_name="ÍNDICE"
    )

    # RESUMO — colunas alinhadas à linha 11 do template:
    # EMPRESA, CNPJ, REGIME_TRIBUTARIO, PERIODO_INI, PERIODO_FIM,
    # TOTAL_NFS_ANALISADAS, TOTAL_ITENS_CRUZADOS, TOTAL_ITENS_USO_CONSUMO,
    # TOTAL_ELEGIVEL, TOTAL_REVISAO, TOTAL_NAO_ELEGIVEL, TOTAL_ORFAOS,
    # VL_CREDITO_PIS, VL_CREDITO_COFINS, VL_CREDITO_TOTAL
    if resumo is not None and resumo.height > 0:
        eh.dump_data_to_sheet(
            excel_thing=wb, data=resumo,
            starting_cell='B12', write_header=False, sheet_name="RESUMO"
        )

    # DETALHES — colunas alinhadas à linha 11 do template (22 colunas B→W):
    # ITEM_KEY, CHV_NFE, COD_PART, RAZAO_SOCIAL, CNPJ_EMIT, NUM_DOC, SER,
    # DT_DOC, CFOP, DESCR_COMPL, CST_PIS, CST_COFINS, ALIQ_PIS, ALIQ_COFINS,
    # VL_ITEM, VL_BC_PIS, VL_BC_COFINS, ELEGIBILIDADE,
    # VL_CREDITO_PIS, VL_CREDITO_COFINS, VL_CREDITO_TOTAL, OBSERVACOES
    if detalhes is not None and detalhes.height > 0:
        eh.dump_data_to_sheet(
            excel_thing=wb, data=detalhes,
            starting_cell='B12', write_header=False, sheet_name="DETALHES"
        )

    # ORFAOS — colunas alinhadas à linha 11 do template (8 colunas B→I):
    # CHAVE_NF, CHV_NFE, COD_PART, NUM_DOC, SER, DT_DOC, VL_DOC, OBRIGACAO_FALTANTE
    if orfaos is not None and orfaos.height > 0:
        eh.dump_data_to_sheet(
            excel_thing=wb, data=orfaos,
            starting_cell='B12', write_header=False, sheet_name="ORFAOS"
        )

    wb.save(filename)
    self.logger.info(f"[U&C] Output salvo (template): {filename}")

