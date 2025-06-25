from datetime import datetime
import datatricks.io.excel_handler as eh
import cruzamento.cruzamento_definition as cd
import os
import polars as pl


def excel_escrituracao(self, empresa, escrituracao, analise, projeto):
    directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.dirname(directory)
    output_folder = self.global_params["output"]

    cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_Check SPED x XML_v5.xlsx')
    wb = eh.open_template(cruzamentos_file)
    company = pl.DataFrame([empresa])

    eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="Índice", write_header=False, starting_cell='B7')
    eh.dump_data_to_sheet(excel_thing=wb, data=escrituracao, starting_cell='B11', write_header=True, sheet_name="SPED x XML")
    eh.dump_data_to_sheet(excel_thing=wb, data=analise, starting_cell='B11', write_header=True, sheet_name="ARQUIVOS_PARA_ANALISE")
    wb.save(output_folder + "\\" + "1. Apter_" + projeto +   " - Check SPED x XML_" +  datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


def excel_receita(self, empresa, Contribuicoes, Fiscal, Notas, NFE, nConsiderada, nProcessado, Anual, Trimestral, Consolidado, Analitico, projeto):
    directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.dirname(directory)
    output_folder = self.global_params["output"]

    if Analitico.height > 0:
        anos = Analitico.select(pl.col(cd.ANO).unique()).to_series().to_list()
        for ano in anos:
            analitico = Analitico.filter(pl.col(cd.ANO) == ano)
            analitico = analitico.drop(cd.ANO)

            anual = Anual.filter(pl.col(cd.ANO) == ano)

            trimestral = Trimestral.filter(pl.col(cd.ANO) == ano)
            trimestral = trimestral.drop(cd.linha)

            consolidado = Consolidado.filter(pl.col(cd.ANO) == ano)
            consolidado = consolidado.drop(cd.ANO, cd.linha)

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
    