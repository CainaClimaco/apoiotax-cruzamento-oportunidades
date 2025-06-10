import os
import sys
import shutil
import cruzamento.Receita as re
import cruzamento.write_excel as we
import cruzamento.Escrituracao as es
import datatricks.io.file_definitions as fd
import cruzamento.cruzamento_definition as cd
import datatricks.sped.sped_definitions as dfn
import cruzamento.file_reader as fr
import datatricks.io.file_helper as fh
from datatricks.commander.prompt_commander import Commander
import cruzamento.write_excel as we


class Sped_cruzamento(Commander):
    def execute(self):
        self.logger.info("Starting application.")
        inbound = self.get_incomming_files()
        inbound = fh.get_sped_filters(inbound)
        operation = self.global_params["form_Tipo"]        


        df_contribuicoes = fr.leitor_sped(inbound, fd.IS_EFDC, dfn.EFDC, cd.PADRAO_EFDC, cd.EFDC)
        df_fiscal = fr.leitor_sped(inbound, fd.IS_EFDF, dfn.EFDF, cd.PADRAO_EFDF, cd.EFDF) 


        match operation.upper():
            case cd.escrituracao:
                empresa, escrituracao, analise = es.process_escrituracao(inbound, df_contribuicoes, df_fiscal, self)
                we.excel_escrituracao(self, empresa, escrituracao, analise)
                
            case cd.receita:
                re.process_receita(inbound,df_contribuicoes, df_fiscal, self)


if __name__ == "__main__":
    if os.path.exists(r'C:\Projetos\projetos\Dados\base_cruzamentos\output'):
        shutil.rmtree(r'C:\Projetos\projetos\Dados\base_cruzamentos\output')
    cmd = Sped_cruzamento(app = 'Sped Cruzamento', path=os.path.abspath(__file__), args=sys.argv)
    cmd.process()
    del(cmd)
    