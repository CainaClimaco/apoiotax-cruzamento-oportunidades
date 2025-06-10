from datetime import datetime
import datatricks.io.excel_handler as eh
import shutil
import os
import polars as pl


def excel_escrituracao(self, empresa, escrituracao, analise):
    directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.dirname(directory)
    cruzamentos_file = os.path.join(root_directory, 'assets\\Template_Check SPED x XML_v5.xlsx')
    output_folder = self.global_params["output"]
    wb = eh.open_template(cruzamentos_file)
    company = pl.DataFrame([empresa[1]])

    eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="Índice", write_header=False, starting_cell='B7')
    eh.dump_data_to_sheet(excel_thing=wb, data=escrituracao, starting_cell='B11', write_header=True, sheet_name="SPED x XML")
    eh.dump_data_to_sheet(excel_thing=wb, data=analise, starting_cell='B11', write_header=True, sheet_name="ARQUIVOS_PARA_ANALISE")
    wb.save(output_folder + "\\" + empresa[1] + " Check SPED x XML " + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")




def excel_receita(self, empresa, Contribuicoes, Fiscal, Trimestral, Anual, analise):
    directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.dirname(directory)
    output_folder = self.global_params["output"]

    if analise.heigth > 0:
        cruzamentos_file = os.path.join(root_directory, 'assets\\Template_XML_N_CONSIDERADOS.xlsx')
        wb = eh.open_template(cruzamentos_file)
        company = pl.DataFrame([empresa[1]])

        eh.dump_data_to_sheet(company, excel_thing = wb,sheet_name="ÍNDICE", write_header=False, starting_cell='B6')
        eh.dump_data_to_sheet(excel_thing=wb, data=analise, starting_cell='B12', write_header=False, sheet_name="ARQUIVOS_PARA_ANALISE")
        wb.save(output_folder + "\\" + empresa[1] + "" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".xlsx")
