import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd
import cruzamento.cruzamento_definition as cd
import cruzamento.file_reader as fr
import cruzamento.analise as an
import cruzamento.empresa as em


def process_escrituracao(inbound, df_contribuicoes, df_fiscal, self):

    NFe, xml_erro = fr.leitor_nfe(inbound, fd.IS_NFE, cd.NFE, cd.status_xml)
    
    analise = an.analise(NFe, xml_erro, df_contribuicoes, df_fiscal, self, inbound)
    
    Contribuicoes = (df_contribuicoes.select(['Registro', cd.COD_SIT, cd.CHV_NFE, 'Período'])
                    ).filter(pl.col("Registro") == 'C100').unique(subset=[cd.CHV_NFE], keep="first").filter(~pl.all_horizontal(pl.all().is_null()))
    Fiscal = (df_fiscal.select(['Registro', cd.COD_SIT, cd.CHV_NFE, 'Período'])
            ).filter(pl.col("Registro") == 'C100').unique(subset=[cd.CHV_NFE], keep="first").filter(~pl.all_horizontal(pl.all().is_null()))
    NFe = NFe.unique(subset=[cd.ID], keep="first").filter(~pl.all_horizontal(pl.all().is_null()))


    Contribuicoes = Contribuicoes.with_columns(pl.lit("SIM").alias("EFD CONTRIBUIÇÕES"))
    Fiscal = Fiscal.with_columns(pl.lit("SIM").alias("EFD ICMS IPI"))
    NFe = NFe.with_columns(pl.lit("SIM").alias("NFE"))
        

    df_empresa = pl.concat([
        df_contribuicoes.select([cd.NOME, cd.CNPJ, 'Registro']).filter(pl.col("Registro") == '0000'),
        df_fiscal.select([cd.NOME, cd.CNPJ, 'Registro']).filter(pl.col("Registro") == '0000')
    ])
    empresa, cnpj = em.empresa_cnpj(inbound, df_empresa)


    tratamento = NFe.with_columns([
        pl.when(pl.col(cd.CNPJ_DEST).eq(cnpj))
            .then(pl.lit("Emissão Terceiros - Entrada"))
        .when((pl.col(cd.CNPJ_EMIT).eq(cnpj)) & (pl.col(cd.tpNF) == 0))
            .then(pl.lit("Emissão Própria - Entrada")) 
        .when((pl.col(cd.CNPJ_EMIT).eq(cnpj)) & (pl.col(cd.tpNF) == 1))
            .then(pl.lit("Emissão Própria - Saída"))
        .otherwise(pl.lit("Terceiros - Sem Vínculo"))
        .alias("EMISSÃO")  
    ])


    verificacao = pl.concat([
        Contribuicoes.select(pl.col(cd.CHV_NFE),pl.col("Período"), pl.col("EFD CONTRIBUIÇÕES"), pl.col("COD_SIT").alias("COD_SIT_EFDC").cast(pl.Utf8)),
        Fiscal.select(pl.col(cd.CHV_NFE),pl.col("Período"), pl.col("EFD ICMS IPI"), pl.col("COD_SIT").alias("COD_SIT_EFDF").cast(pl.Utf8)),
        tratamento.select(pl.col(cd.CHV_NFE),pl.col(cd.PERÍODO), pl.col("NFE"), pl.col(cd.SITUACAO), pl.col("EMISSÃO"))
        ], how="diagonal")

    verificacao = verificacao.group_by(cd.CHV_NFE).agg([
        pl.col("Período").dt.strftime("%d/%m/%Y").sort(nulls_last=True).first().alias("PERÍODO"),
        pl.col("EFD CONTRIBUIÇÕES").sort(nulls_last=True).first().alias("EFD CONTRIBUIÇÕES"),
        pl.col("COD_SIT_EFDC").sort(nulls_last=True).first().alias("COD_SIT_EFDC"),
        pl.col("EFD ICMS IPI").sort(nulls_last=True).first().alias("EFD ICMS IPI"),
        pl.col("COD_SIT_EFDF").sort(nulls_last=True).first().alias("COD_SIT_EFDF"),
        pl.col("NFE").sort(nulls_last=True).first().alias("NFE"),
        pl.col(cd.SITUACAO).sort(nulls_last=True).first().alias(cd.SITUACAO),
        pl.col("EMISSÃO").sort(nulls_last=True).first().alias("EMISSÃO")
    ])
        

    df_situacao = pl.read_excel(
        source = cd.CAMINHO_SITUACAO,
        engine = "openpyxl")
    
    situacao = verificacao.join(df_situacao, left_on="COD_SIT_EFDC", right_on="Código", how="left"
                                ).join(df_situacao, left_on="COD_SIT_EFDF", right_on="Código", how="left")


    escrituracao = situacao.sort('PERÍODO', cd.CHV_NFE )

    return escrituracao, empresa, analise