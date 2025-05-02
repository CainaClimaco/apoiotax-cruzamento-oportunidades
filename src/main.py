import os, sys
from datatricks.commander.prompt_commander import Commander
import datatricks.sped.content as sp
import datatricks.io.file_helper as fh
import datatricks.sped.sped_definitions as dfn
import datatricks.sped.conversor as cv
import datatricks.io.excel_handler as eh
import datatricks.io.file_definitions as fd
from datatricks.sped.file_identifier import is_NFe
import shutil
from pathlib import Path
import openpyxl
import polars as pl
import numpy as np



class Sped_cruzamento(Commander):

    def execute(self):
        self.logger.info("Starting application.")
        inbound = self.get_incomming_files()
        inbound = fh.get_sped_filters(inbound)
        assets_path = self.get_assets_files() 

        df_efdc_padrao = pl.read_excel(
            source = "src\\assets\\Registros EFD Contribuicoes v7.xlsx",
            engine = "openpyxl").filter((pl.col("Registro") == 'C100') & (pl.col("Versao") == "006")) 

        contadores_efdc = {}
        novo_campo_efdc = []

        for valor in df_efdc_padrao['Campo']:
            valor_str = str(valor)
            contadores_efdc[valor_str] = contadores_efdc.get(valor_str, 0) + 1
            if contadores_efdc[valor_str] == 1:
                novo_campo_efdc.append(valor_str)
            else:
                novo_campo_efdc.append(f"{valor_str}_{contadores_efdc[valor_str]-1}")

        df_efdc_padrao = df_efdc_padrao.with_columns([
            pl.Series("Campo", novo_campo_efdc)
        ])

        df_efdc_transpose = df_efdc_padrao.transpose(column_names="Campo")

        df_efdc_transpose = (df_efdc_transpose.with_columns([
            pl.col(col).map_elements(lambda x: None if isinstance(x, str) else x, return_dtype=df_efdc_transpose.schema[col])
            for col in df_efdc_transpose.columns
        ]).with_columns([pl.lit(None).alias("Período")]).unique(subset=["REG"], keep="first"))
        df_efdc_transpose = df_efdc_transpose.rename({
            'REG': 'Registro',
            'COD_SIT;':'COD_SIT'})

        df_efdf_padrao = pl.read_excel(
            source = "src\\assets\\Registros EFD ICMS IPI.xlsx",
            engine = "openpyxl").filter((pl.col("Registro") == 'C100') & (pl.col("Versao") == "018")) 

        contadores_efdf = {}
        novo_campo_efdf = []

        for valor in df_efdf_padrao['Campo']:
            valor_str = str(valor)
            contadores_efdf[valor_str] = contadores_efdf.get(valor_str, 0) + 1
            if contadores_efdf[valor_str] == 1:
                novo_campo_efdf.append(valor_str)
            else:
                novo_campo_efdf.append(f"{valor_str}_{contadores_efdf[valor_str]-1}")

        df_efdf_padrao = df_efdf_padrao.with_columns([
            pl.Series("Campo", novo_campo_efdf)
        ])

        df_efdf_transpose = df_efdf_padrao.transpose(column_names="Campo")

        df_efdf_transpose = (
            df_efdf_transpose.with_columns([
                pl.col(col).map_elements(
                    lambda x: None if isinstance(x, str) else x,
                    return_dtype=df_efdf_transpose.schema[col]
                )
                for col in df_efdf_transpose.columns
            ]).with_columns([pl.lit(None).alias("Período")]).unique(subset=["REG"], keep="first"))
        df_efdf_transpose = df_efdf_transpose.rename({'REG': 'Registro'})

        df_asset_contrib = cv.read_assets(assets_path, dfn.EFDC)
       
        if inbound is not None and not inbound.filter(pl.col(fd.IS_EFDC)).is_empty():
            df_efdc = inbound.filter(pl.col(fd.IS_EFDC).map_elements(lambda x: x, return_dtype=pl.Boolean))
            df_contribuicoes = cv.quebra(df_efdc, df_asset_contrib, dfn.EFDC)
            df_contribuicoes = df_contribuicoes.rename({
            'field_7': 'NOME',
            'Quebra CNPJ': 'CNPJ',
            'field_10': 'COD_SIT',
            'field_13': 'CHV_NFE'
            })
        else:
            df_contribuicoes = df_efdc_transpose

        
        
        df_asset_fiscal = cv.read_assets(assets_path, dfn.EFDF)
        if inbound is not None and not inbound.filter(pl.col(fd.IS_EFDF)).is_empty():
            df_efdf = inbound.filter(pl.col(fd.IS_EFDF).map_elements(lambda x: x, return_dtype=pl.Boolean))
            df_fiscal = cv.quebra(df_efdf, df_asset_fiscal, dfn.EFDF)
            df_fiscal = df_fiscal.rename({
            'field_7': 'NOME',
            'Quebra CNPJ': 'CNPJ',
            'field_10': 'COD_SIT',
            'field_13': 'CHV_NFE'
            })
        else:
            df_fiscal = df_efdf_transpose 
        
        
        df_asset = pl.read_excel(
            source = "src\\assets\\Situacao_NF-e.xlsx",
            engine = "openpyxl")
        
        caminhoNFe = (inbound.filter(pl.col(fd.FILE_NAME).map_elements(lambda x: is_NFe(x), return_dtype=pl.Boolean))
        .select(fd.FULL_PATH)       
        .item(0, 0))

        dataframeNFe = pl.read_excel(
            source = caminhoNFe,
            engine = "openpyxl",
            sheet_name = 'NFe'
        ) 
        
        FileName = dataframeNFe.with_columns([
            pl.col("file_path").map_elements(lambda x: Path(x).name, return_dtype=pl.String).alias("FileName")
        ])

        dataframeNFe = dataframeNFe.rename({
            'infNFe_ide_dhEmi': 'Período',
            'NFe_infNFe_Id': 'Id',
            'infNFe_emit_CNPJ': 'CNPJ_EMIT',
            'infNFe_dest_CNPJ': 'CNPJ_DEST',
            'protNFe_infProt_xMotivo':'xMotivo',
            'det_prod_CFOP':'CFOP',
            'protNFe_infProt_chNFe':'CHV_NFE'})
        
        
        NFe = dataframeNFe.unique(subset=["CHV_NFE"], keep="first")

  
        NFe = NFe.drop_nulls(subset=["CHV_NFE"])
        NFe = dataframeNFe.select(['Período', 'CHV_NFE', 'xMotivo', 'Id', 'CFOP', 'CNPJ_EMIT','CNPJ_DEST'])
        NFe = NFe.with_columns(pl.col("Período").str.to_datetime().cast(pl.Date), pl.col("CFOP").cast(pl.Int32))

        Contribuicoes = (df_contribuicoes.select(['Registro', 'COD_SIT', 'CHV_NFE', 'Período'])).filter(pl.col("Registro") == 'C100')
        Contribuicoes = Contribuicoes.unique(subset=["CHV_NFE"], keep="first")

        Fiscal = (df_fiscal.select(['Registro', 'COD_SIT', 'CHV_NFE', 'Período'])).filter(pl.col("Registro") == 'C100')
        Fiscal = Fiscal.unique(subset=["CHV_NFE"], keep="first")
       
        PeriodoNotas = pl.concat([
            df_contribuicoes.select(['CHV_NFE', 'Período']),
            df_fiscal.select(['CHV_NFE', 'Período']),
            NFe.select(['CHV_NFE', 'Período'])
        ])
        PeriodoNotas.unique(subset=["CHV_NFE"], keep="first")

        
        empresaCNPJ =  pl.concat([
            df_contribuicoes.select(['NOME', 'CNPJ']),
            df_contribuicoes.select(['NOME', 'CNPJ'])
        ])
        empresaCNPJ = empresaCNPJ.unique(subset=["CNPJ"], keep="first")
        empresaNome = (empresaCNPJ.select(['NOME']).item(0,0))
        cnpj = (empresaCNPJ.select(["CNPJ"]).item(0,0))


        tratamento = (NFe.with_columns([
            pl.when(pl.col("CNPJ_DEST") == cnpj)
                .then(pl.lit("Emissão Terceiros - Entrada"))
            .when((pl.col("CNPJ_EMIT") == cnpj)  & (pl.col("CFOP")<4000))
                .then(pl.lit("Emissão Própria - Entrada")) 
            .when((pl.col("CNPJ_EMIT") == cnpj) & (pl.col("CFOP")>4000))
                .then(pl.lit("Emissão Própria - Saída"))
            .otherwise (pl.lit("Terceiros - Sem Vínculo"))
            .alias("Tipo")  
        ])
        .select(['Período', 'CHV_NFE', 'xMotivo', 'Id', 'CFOP', 'CNPJ_EMIT','CNPJ_DEST', 'Tipo']))

        Contribuicoes = Contribuicoes.with_columns(
        pl.lit("SIM").alias("EFD CONTRIBUIÇÕES"))
        Fiscal = Fiscal.with_columns(
        pl.lit("SIM").alias("EFD ICMS IPI"))
        NFe = NFe.with_columns(
        pl.lit("SIM").alias("NFE"))

        verificação = pl.concat([
            Contribuicoes.select(pl.col("CHV_NFE"),pl.col("Período"), pl.col("EFD CONTRIBUIÇÕES"), pl.col("COD_SIT").alias("COD_SIT_EFDC").cast(pl.Utf8)),
            Fiscal.select(pl.col("CHV_NFE"),pl.col("Período"), pl.col("EFD ICMS IPI"), pl.col("COD_SIT").alias("COD_SIT_EFDF").cast(pl.Utf8)),
            NFe.select(pl.col("CHV_NFE"),pl.col("Período"), pl.col("NFE"), pl.col("xMotivo").alias("SITUAÇÃO NFE")),
            tratamento.select( pl.col("Tipo"))
            ],  how="diagonal")
        
        verificação = verificação.unique(subset=["CHV_NFE"], keep="first")

        situacaoContribuicao  = df_asset.rename({
            "Código" : "COD_SIT_EFDC",
            "Descrição " : "DESC_COD_SIT_EFDC"
        })
        situacaoFiscal  = df_asset.rename({
            "Código" : "COD_SIT_EFDF",
            "Descrição " : "DESC_COD_SIT_EFDF"
        })

        situacao = verificação.join(situacaoContribuicao, on="COD_SIT_EFDC", how="left")
        situacao = situacao.join(situacaoFiscal, on="COD_SIT_EFDF", how="left")
        situacao = situacao.select(pl.col("CHV_NFE"),pl.col("Período").alias("PERÍODO"), pl.col("EFD CONTRIBUIÇÕES"), pl.col("COD_SIT_EFDC"),pl.col("DESC_COD_SIT_EFDC"), pl.col("EFD ICMS IPI") ,pl.col("COD_SIT_EFDF"), pl.col("DESC_COD_SIT_EFDF"), pl.col("NFE"), pl.col("SITUAÇÃO NFE"), pl.col("Tipo").alias("EMISSÃO") )




if __name__ == "__main__":
    if os.path.exists(r'C:\Projetos\projetos\Dados\nfeExcel\output'):
        shutil.rmtree(r'C:\Projetos\projetos\Dados\nfeExcel\output')
    cmd = Sped_cruzamento(app = 'Sped Cruzamento', path=os.path.abspath(__file__), args=sys.argv)
    cmd.process()
    del(cmd)
    