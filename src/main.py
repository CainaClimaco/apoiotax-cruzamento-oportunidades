import os
import sys
import cruzamento.Receita as re
import cruzamento.Escrituracao as es
import datatricks.io.file_definitions as fd
import cruzamento.cruzamento_definition as cd
import datatricks.sped.sped_definitions as dfn
import cruzamento.file_reader as fr
import datatricks.io.file_helper as fh
from datatricks.commander.prompt_commander import Commander


class Sped_cruzamento(Commander):
    def execute(self):
        self.logger.info("Starting application.")
        inbound = self.get_incomming_files()
        inbound = fh.get_sped_filters(inbound)
        operation = self.global_params["form_Tipo"]
        projeto = self.global_params["form_Solicitação"]
        path_env = f'{self.global_params['env_path']}/azure.env'
 


        match operation.upper():
            case cd.escrituracao:
                df_contribuicoes = fr.leitor_sped(inbound, fd.IS_EFDC, dfn.EFDC, cd.EFDC, cd.reg_escri_C, path_env)
                df_fiscal = fr.leitor_sped(inbound, fd.IS_EFDF, dfn.EFDF,  cd.EFDF, cd.reg_escri_F, path_env)
                es.process_escrituracao(inbound, df_contribuicoes, df_fiscal, self, projeto)

            case cd.receita:
                df_contribuicoes = fr.leitor_sped(inbound, fd.IS_EFDC, dfn.EFDC, cd.EFDC, cd.reg_receita_C, path_env)
                df_fiscal = fr.leitor_sped(inbound, fd.IS_EFDF, dfn.EFDF,  cd.EFDF, cd.reg_receita_F, path_env)
                re.process_receita(inbound, df_contribuicoes, df_fiscal, self, projeto, path_env)

            case cd.fase1:
                import cruzamento.fase1 as f1
                df_contribuicoes = fr.leitor_sped(inbound, fd.IS_EFDC, dfn.EFDC, cd.EFDC, cd.reg_fase1_C, path_env)
                df_fiscal = fr.leitor_sped(inbound, fd.IS_EFDF, dfn.EFDF,  cd.EFDF, cd.reg_fase1_F, path_env)
                f1.process_fase1(inbound, df_contribuicoes, df_fiscal, self, projeto, path_env)


if __name__ == "__main__":
    cmd = Sped_cruzamento(app = 'Sped Cruzamento', path=os.path.abspath(__file__), args=sys.argv)
    cmd.process()
    del(cmd)
    