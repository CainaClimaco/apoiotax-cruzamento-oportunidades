import os, sys
from datatricks.commander.prompt_commander import Commander
import datatricks.sped.content as sp
import datatricks.io.file_helper as fh
import datatricks.sped.sped_definitions as sd
import datatricks.io.excel_handler as eh
import datatricks.io.file_definitions as fd
from datatricks.sped.file_identifier import is_NFe, is_Contribuicoes, is_Fiscal
import shutil
from pathlib import Path
import openpyxl
import polars as pl



class Sped_cruzamento(Commander):

    def execute(self):
        self.logger.info("Starting application.")
        inbound = self.get_incomming_files()

        df_asset = pl.read_excel(
            source = r"src\assets\Situacao_NF-e.xlsx",
            engine = "openpyxl")
        # print(df_asset)

        caminhoFiscal = (inbound.filter(pl.col(fd.FILE_NAME).map_elements(lambda x: is_Fiscal(x), return_dtype=pl.Boolean))
        .select(fd.FULL_PATH)       
        .item(0, 0))


        dataframeFiscal = pl.read_excel(
            source = caminhoFiscal,
            engine = "openpyxl",
            sheet_name = 'C100'
        ) 

        dataframeEmpresaF = pl.read_excel(
            source = caminhoFiscal,
            engine = "openpyxl",
            sheet_name = '0000'
        ) 

        caminhoContribuicoes = (inbound.filter(pl.col(fd.FILE_NAME).map_elements(lambda x: is_Contribuicoes(x), return_dtype=pl.Boolean))
        .select(fd.FULL_PATH)       
        .item(0, 0))

        dataframeContribuicoes = pl.read_excel(
            source = caminhoContribuicoes,
            engine = "openpyxl",
            sheet_name = 'C100'
        ) 
        dataframeEmpresaC = pl.read_excel(
            source = caminhoContribuicoes,
            engine = "openpyxl",
            sheet_name = '0000'
        ) 

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
        
        NFe = dataframeNFe.select(['Período', 'CHV_NFE', 'xMotivo', 'Id', 'CFOP', 'CNPJ_EMIT','CNPJ_DEST'])
        NFe = dataframeNFe.unique(subset=["CHV_NFE"], keep="first")
        
        NFe = NFe.with_columns(
        pl.col("Período").str.strptime(pl.Datetime, strict=False))

        NFe = NFe.with_columns(pl.col("Período").cast(pl.Datetime("us", None)))

        NFe = NFe.with_columns([
        pl.col("CFOP").cast(pl.Int32)])
  
        NFe = NFe.drop_nulls(subset=["CHV_NFE"])

        Contribuicoes = (dataframeContribuicoes.select(['Registro', 'COD_SIT', 'CHV_NFE', 'Período']))
        Contribuicoes = dataframeContribuicoes.unique(subset=["CHV_NFE"], keep="first")
        
        Fiscal = (dataframeFiscal.select(['Registro', 'COD_SIT', 'CHV_NFE', 'Período']))
        Fiscal = dataframeFiscal.unique(subset=["CHV_NFE"], keep="first")
        
       
        PeriodoNotas = pl.concat([
            Contribuicoes.select(['CHV_NFE', 'Período']),
            Fiscal.select(['CHV_NFE', 'Período']),
            NFe.select(['CHV_NFE', 'Período'])
        ])
        PeriodoNotas.unique(subset=["CHV_NFE"], keep="first")
        print(PeriodoNotas)

        empresaCNPJ =  pl.concat([
            dataframeEmpresaC.select(['NOME', 'CNPJ']),
            dataframeEmpresaF.select(['NOME', 'CNPJ'])
        ])
        empresaCNPJ = empresaCNPJ.unique(subset=["CNPJ"], keep="first")
        empresaNome = (empresaCNPJ.select(['NOME']).item(0,0))
        cnpj = (empresaCNPJ.select(["CNPJ"]).item(0,0))

        print(empresaNome)

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

        # print(verificação)

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

        print(situacao)




if __name__ == "__main__":
    if os.path.exists(r'C:\Projetos\projetos\Dados\Cruzamentos\output'):
        shutil.rmtree(r'C:\Projetos\projetos\Dados\Cruzamentos\output')
    cmd = Sped_cruzamento(app = 'Sped Cruzamento', path=os.path.abspath(__file__), args=sys.argv)
    cmd.process()
    del(cmd)
    