import os
from datetime import datetime
import datatricks.io.excel_handler as eh


def excel_escrituracao(self, empresa, escrituracao, analise):
    template_path = self.global_params['template_files'][1]
    template = eh.open_template(template_path)
    ws = template.active
    ws['B7'] = empresa.upper()
        
    self.logger.info("Writing Report of Processed Files")
    eh.dump_data_to_sheet(excel_thing=template, data=escrituracao, starting_cell='B11', write_header=True, sheet_name="SPED x XML")
    eh.dump_data_to_sheet(excel_thing=template, data=analise, starting_cell='B11', write_header=True, sheet_name="ARQUIVOS_PARA_ANALISE")
    template.save(self.global_params['template_files'][1])
    os.rename(self.global_params['template_files'][1], f'{self.global_params["output"]}Check SPED x XML{datetime.now():%d-%m-%Y_%H-%M-%S}.xlsx')
    self.logger.info("Ending execution.")


def excel_receita(self, empresa, df, analise):
    template_path = self.global_params['template_files'][0]
    template = eh.open_template(template_path)
    ws = template.active
    ws['B7'] = empresa.upper()