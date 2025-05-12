import os, sys
from datatricks.commander.prompt_commander import Commander
import datatricks.sped.sped_definitions as dfn
import datatricks.io.file_helper as fh
import datatricks.io.excel_handler as eh
import datatricks.io.file_definitions as fd
import cruzamento.cruzamento_definition as cd
import cruzamento.cruzamento as cr
import cruzamento.analise as an
import shutil
import polars as pl
from datetime import datetime
from pathlib import Path


class Sped_cruzamento(Commander):

    def execute(self):
        self.logger.info("Starting application.")
        inbound = self.get_incomming_files()
        inbound = fh.get_sped_filters(inbound)
        assets_path = self.get_assets_files() 

        df_contribuicoes = cr.leitor_sped(inbound, fd.IS_EFDC, dfn.EFDC, cd.CAMINHO_EFDC, cd.VERSAO_EFDC, assets_path, cd.PADRAO_EFDC, cd.EFDC)
        df_fiscal = cr.leitor_sped(inbound, fd.IS_EFDF, dfn.EFDF, cd.CAMINHO_EFDF, cd.VERSAO_EFDF, assets_path, cd.PADRAO_EFDF, cd.EFDF)
        df_nfe = cr.leitor_nfe(inbound, fd.IS_NFE, cd.NFE)

        # Análise: Tratativa para arquivos não processados
        erro = an.count_arquivos(df_nfe, df_contribuicoes, df_fiscal, self)        
        xml = an.filtrar_fora_do_padrao(inbound, '.xml', pl.col(fd.IS_NFE), cd.status_xml)
        txt = an.filtrar_fora_do_padrao(inbound, '.txt', pl.col(fd.IS_EFDC) | pl.col(fd.IS_EFDF), cd.status_txt)
        nfe_duplicada = an.nfe_duplicada(df_nfe, cd.ID)

        analise = pl.concat([xml, txt, nfe_duplicada, erro], how="diagonal")
        analise = analise.sort("STATUS ARQUIVO", 'NOME DO ARQUIVO').filter(~pl.all_horizontal(pl.all().is_null()))

        # Cruzamento
        Contribuicoes = (df_contribuicoes.select(['Registro', cd.COD_SIT, cd.CHV_NFE, 'Período'])
                         ).filter(pl.col("Registro") == 'C100').unique(subset=[cd.CHV_NFE], keep="first").filter(pl.col(cd.CHV_NFE).is_not_null())
        Fiscal = (df_fiscal.select(['Registro', cd.COD_SIT, cd.CHV_NFE, 'Período'])
                  ).filter(pl.col("Registro") == 'C100').unique(subset=[cd.CHV_NFE], keep="first").filter(pl.col(cd.CHV_NFE).is_not_null())
        NFe = df_nfe.unique(subset=[cd.ID], keep="first")

        PeriodoNotas = pl.concat([
            Contribuicoes.select([cd.CHV_NFE, 'Período']),
            Fiscal.select([cd.CHV_NFE, 'Período']),
            NFe.select([cd.CHV_NFE,cd.PERÍODO])
        ])
        PeriodoNotas.unique(subset=[cd.CHV_NFE], keep="first")

        if (inbound.filter(pl.col(fd.IS_EFDC)).is_empty()) & (inbound.filter(pl.col(fd.IS_EFDC)).is_empty()):
            empresa = ""
            cnpj = ""
        else:
            empresaCNPJ =  pl.concat([
                df_contribuicoes.select([cd.NOME, cd.CNPJ, 'Registro']).filter(pl.col("Registro") == '0000'),
                df_fiscal.select([cd.NOME, cd.CNPJ, 'Registro']).filter(pl.col("Registro") == '0000')
            ]).unique(subset=[cd.CNPJ], keep="first")
            empresa = (empresaCNPJ.select([cd.NOME]).item(0,0))
            cnpj = (empresaCNPJ.select([cd.CNPJ]).item(0,0))

        Contribuicoes = Contribuicoes.with_columns(pl.lit("SIM").alias("EFD CONTRIBUIÇÕES"))
        Fiscal = Fiscal.with_columns(pl.lit("SIM").alias("EFD ICMS IPI"))
        NFe = NFe.with_columns(pl.lit("SIM").alias("NFE"))
       
        tratamento = NFe.with_columns([
            pl.when(cd.CNPJ_DEST == cnpj)
                .then(pl.lit("Emissão Terceiros - Entrada"))
            .when((cd.CNPJ_EMIT == cnpj)  & (pl.col(cd.CFOP)<4000))
                .then(pl.lit("Emissão Própria - Entrada")) 
            .when((cd.CNPJ_EMIT == cnpj) & (pl.col(cd.CFOP)>4000))
                .then(pl.lit("Emissão Própria - Saída"))
            .otherwise (pl.lit("Terceiros - Sem Vínculo"))
            .alias("EMISSÃO")  
        ])        
        
        verificacao = pl.concat([
            Contribuicoes.select(pl.col(cd.CHV_NFE),pl.col("Período"), pl.col("EFD CONTRIBUIÇÕES"), pl.col("COD_SIT").alias("COD_SIT_EFDC").cast(pl.Utf8)),
            Fiscal.select(pl.col(cd.CHV_NFE),pl.col("Período"), pl.col("EFD ICMS IPI"), pl.col("COD_SIT").alias("COD_SIT_EFDF").cast(pl.Utf8)),
            tratamento.select(pl.col(cd.CHV_NFE),pl.col(cd.PERÍODO), pl.col("NFE"), pl.col(cd.SITUACAO), pl.col("EMISSÃO"))
            ], how="diagonal")
        
        verificacao = verificacao.unique(subset=[cd.CHV_NFE], keep="first")

        df_situacao = pl.read_excel(
            source = cd.CAMINHO_SITUACAO,
            engine = "openpyxl")

        situacao = verificacao.join(df_situacao, left_on="COD_SIT_EFDC", right_on="Código", how="left"
                                    ).join(df_situacao, left_on="COD_SIT_EFDF", right_on="Código", how="left", suffix="_efdf")

        cruzamento = situacao.select(pl.col(cd.CHV_NFE),
                                   pl.col("Período").alias("PERÍODO"), 
                                   pl.col("EFD CONTRIBUIÇÕES"), 
                                   pl.col("COD_SIT_EFDC"),
                                   pl.col("Descrição ").alias("DESC_COD_SIT_EFDC"), 
                                   pl.col("EFD ICMS IPI"),
                                   pl.col("COD_SIT_EFDF"), 
                                   pl.col("Descrição _efdf").alias("DESC_COD_SIT_EFDF"), 
                                   pl.col("NFE"), 
                                   pl.col("EMISSÃO"),
                                   pl.col("SITUAÇÃO NFE"))
                                   
        cruzamento = cruzamento.sort(cd.CHV_NFE, 'PERÍODO' ).filter(pl.col(cd.CHV_NFE).is_not_null())
        print(cruzamento)
        
        ### Preenchimento do Excel - Output

        template = eh.open_template(self.global_params['template_files'][0])
        ws = template.active
        ws['B7'] = empresa
        
        self.logger.info("Writing Report of Processed Files")
        eh.dump_data_to_sheet(excel_thing=template, data=cruzamento, starting_cell='B11', write_header=True, sheet_name="SPED x XML")
        eh.dump_data_to_sheet(excel_thing=template, data=analise, starting_cell='B11', write_header=True, sheet_name="ARQUIVOS_PARA_ANALISE")
        template.save(self.global_params['template_files'][0])
        os.rename(self.global_params['template_files'][0], f'{self.global_params["output"]}Check SPED x XML{datetime.now():%d-%m-%Y_%H-%M-%S}.xlsx')
        
        self.logger.info("Ending execution.")
        
                      
if __name__ == "__main__":
    if os.path.exists(r'C:\Users\Apter\Documents\Projetos\projetos\Dados\base_cruzamentos\output'):
        shutil.rmtree(r'C:\Users\Apter\Documents\Projetos\projetos\Dados\base_cruzamentos\output')
    cmd = Sped_cruzamento(app = 'Sped Cruzamento', path=os.path.abspath(__file__), args=sys.argv)
    cmd.process()
    del(cmd)
    