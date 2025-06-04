import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd
import cruzamento.file_reader as fr
import cruzamento.analise as an
import cruzamento.empresa as em
import json


def process_receita(inbound, df_contribuicoes, df_fiscal, self):

        df_nfe, xml_erro = fr.leitor_nfe(inbound, fd.IS_NFE, cd.NFE, cd.status_xml)
        NFe = df_nfe.unique(subset=[cd.ID], keep="first")

        analise = an.analise(df_nfe, xml_erro, df_contribuicoes, df_fiscal, self, inbound)

        df_situacao = pl.read_excel(
        source = cd.CAMINHO_COD_SIT,
        engine = "openpyxl")

        df_cfop = pl.read_excel(
        source = cd.CAMINHO_CFOP,
        engine = "openpyxl")


        df = pl.read_json(cd.json_path)

        lista_contr = df.get_column("Registros_contri")
        Contribuicoes = df_contribuicoes.filter(pl.col("Registro").is_in(lista_contr))

        lista_fiscal = df.get_column("Registros_fiscal")
        Fiscal = df_fiscal.filter(pl.col("Registro").is_in(lista_fiscal))


        df_empresa = pl.concat([
                df_contribuicoes.select([cd.NOME, cd.CNPJ, 'Registro']).filter(pl.col("Registro") == '0000'),
                df_fiscal.select([cd.NOME, cd.CNPJ, 'Registro']).filter(pl.col("Registro") == '0000')
                # ,df_nfe.select([cd.NOME, cd.CNPJ])
                ], how="diagonal")
        empresa = em.empresa_cnpj(inbound, df_empresa)


        receita = 0
        return receita, empresa, analise