import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd
import cruzamento.write_excel as we
import cruzamento.file_reader as fr
import cruzamento.analise as an
import cruzamento.empresa as em


def process_escrituracao(inbound, df_contribuicoes, df_fiscal, self, projeto):

    regex_list = []

    NFe, xml_erro = fr.leitor_nfe(inbound, fd.IS_NFE, cd.status_xml, regex_list, rename=cd.NFE[cd.rename_e], field_list=cd.NFE[cd.CAMPOS_ESCRITURACAO])
    
    NFe = NFe.with_columns(
                pl.col(cd.PERÍODO).str.slice(0,10).str.strptime(pl.Date, strict=False),
                pl.col(cd.tpNF).cast(pl.Int32))
    
    analise = an.analise(NFe, xml_erro, df_contribuicoes, df_fiscal, self, inbound)
    
    Contribuicoes = (df_contribuicoes.select([cd.Registro, cd.COD_SIT, cd.CHV_NFE, cd.PERÍODO])
                    ).filter(pl.col(cd.Registro) == 'C100').unique(subset=[cd.CHV_NFE], keep="first"
                    ).filter(~pl.all_horizontal(pl.all().is_null()))
    
    Fiscal = (df_fiscal.select([cd.Registro, cd.COD_SIT, cd.CHV_NFE, cd.PERÍODO])
            ).filter(pl.col(cd.Registro) == 'C100').unique(subset=[cd.CHV_NFE], keep="first"
            ).filter(~pl.all_horizontal(pl.all().is_null()))
    
    NFe = NFe.unique(subset=[cd.ID], keep="first").filter(~pl.all_horizontal(pl.all().is_null()))


    Contribuicoes = Contribuicoes.with_columns(pl.lit("SIM").alias(cd.EFD_CONTRIBUICOES))
    Fiscal = Fiscal.with_columns(pl.lit("SIM").alias(cd.EFD_ICMS_IPI))
    NFe = NFe.with_columns(pl.lit("SIM").alias(cd.NFe))
        

    
    empresa, cnpj = em.empresa_cnpj(inbound, df_fiscal, df_contribuicoes)


    tratamento = NFe.with_columns([
        pl.when(pl.col(cd.CNPJ_DEST).eq(cnpj))
            .then(pl.lit("Emissão Terceiros - Entrada"))
        .when((pl.col(cd.CNPJ).eq(cnpj)) & (pl.col(cd.tpNF) == 0))
            .then(pl.lit("Emissão Própria - Entrada")) 
        .when((pl.col(cd.CNPJ).eq(cnpj)) & (pl.col(cd.tpNF) == 1))
            .then(pl.lit("Emissão Própria - Saída"))
        .otherwise(pl.lit("Terceiros - Sem Vínculo"))
        .alias(cd.EMISSAO)  
    ])


    verificacao = pl.concat([
        Contribuicoes.select(pl.col(cd.CHV_NFE),pl.col(cd.PERÍODO), pl.col(cd.EFD_CONTRIBUICOES), pl.col(cd.COD_SIT).alias(cd.COD_SIT_EFDC).cast(pl.Utf8)),
        Fiscal.select(pl.col(cd.CHV_NFE),pl.col(cd.PERÍODO), pl.col(cd.EFD_ICMS_IPI), pl.col(cd.COD_SIT).alias(cd.COD_SIT_EFDF).cast(pl.Utf8)),
        tratamento.select(pl.col(cd.CHV_NFE),pl.col(cd.PERÍODO), pl.col(cd.NFe), pl.col(cd.SITUACAO), pl.col(cd.EMISSAO))
        ], how="diagonal")

    verificacao = verificacao.group_by(cd.CHV_NFE).agg([
        pl.col(cd.PERÍODO).dt.strftime("%d/%m/%Y").sort(nulls_last=True).first().alias("PERÍODO"),
        pl.col(cd.EFD_CONTRIBUICOES).sort(nulls_last=True).first().alias(cd.EFD_CONTRIBUICOES),
        pl.col(cd.COD_SIT_EFDC).sort(nulls_last=True).first().alias(cd.COD_SIT_EFDC),
        pl.col(cd.EFD_ICMS_IPI).sort(nulls_last=True).first().alias(cd.EFD_ICMS_IPI),
        pl.col(cd.COD_SIT_EFDF).sort(nulls_last=True).first().alias(cd.COD_SIT_EFDF),
        pl.col(cd.NFe).sort(nulls_last=True).first().alias(cd.NFe),
        pl.col(cd.SITUACAO).sort(nulls_last=True).first().alias(cd.SITUACAO),
        pl.col(cd.EMISSAO).sort(nulls_last=True).first().alias(cd.EMISSAO)
    ])
        

    df_situacao = pl.read_excel(
        source = cd.CAMINHO_SITUACAO,
        engine = "openpyxl")
    
    situacao = verificacao.join(df_situacao, left_on=cd.COD_SIT_EFDC, right_on=cd.CODIGO, how="left"
                                ).join(df_situacao, left_on=cd.COD_SIT_EFDF, right_on=cd.CODIGO, how="left")


    escrituracao = situacao.sort('PERÍODO', cd.CHV_NFE )

    we.excel_escrituracao(self, empresa, escrituracao, analise, projeto)


