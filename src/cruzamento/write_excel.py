from datetime import datetime
import datatricks.io.excel_handler as eh
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


def excel_receita(self, empresa, Contribuicoes, Fiscal, NFE, nConsiderada, analise, projeto):
    directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.dirname(directory)
    output_folder = self.global_params["output"]

    
    if Fiscal.height > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_EFDFISCAL.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
        eh.dump_data_to_sheet(excel_thing=wb, data=Fiscal, starting_cell='B12', write_header=False, sheet_name="EFD ICMS IPI")
        wb.save(output_folder + "\\" + "2.Apter_EFD_Fiscal_" + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if Contribuicoes.height > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_EFDCONTRIBUICOES.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
        eh.dump_data_to_sheet(excel_thing=wb, data=Contribuicoes, starting_cell='B12', write_header=False, sheet_name="EFD CONTRIBUICOES")
        wb.save(output_folder + "\\" + "3.Apter_EFD_Contribuições - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if NFE.height > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_XML.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
        eh.dump_data_to_sheet(excel_thing=wb, data=NFE, starting_cell='B12', write_header=False, sheet_name="XML")
        wb.save(output_folder + "\\" + "5.Apter_XML - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")


    if nConsiderada.height > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_XML_N_CONSIDERADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
        eh.dump_data_to_sheet(excel_thing=wb, data=nConsiderada, starting_cell='B12', write_header=False, sheet_name="XML - N_CONSIDERADOS")
        wb.save(output_folder + "\\" + "6. Apter_Não_Considerados - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    

    if analise.height > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\templates\\Template_N_PROCESSADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa])

        eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
        eh.dump_data_to_sheet(excel_thing=wb, data=analise, starting_cell='B12', write_header=False, sheet_name="ARQUIVOS_PARA_ANALISE")
        wb.save(output_folder + "\\" + "7.Apter_Não_Processados - " + projeto + "_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
    