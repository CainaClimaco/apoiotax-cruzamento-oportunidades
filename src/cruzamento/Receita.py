import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd
import cruzamento.write_excel as we
import cruzamento.file_reader as fr
import cruzamento.analise as an
import cruzamento.empresa as em
import cruzamento.dados_receita as dr


def process_receita(inbound, df_contribuicoes, df_fiscal, self, projeto):

        df_nfe, xml_erro = dr.processXML(inbound)

        erro = an.count_arquivos(df_nfe, df_contribuicoes, df_fiscal, self)  
        xml = an.filtrar_fora_do_padrao(inbound, '.xml', pl.col(fd.IS_NFE), cd.status_xml)
        txt = an.filtrar_fora_do_padrao(inbound, '.txt', pl.col(fd.IS_EFDC) | pl.col(fd.IS_EFDF), cd.status_txt)
        nProcessado = pl.concat([xml, txt, xml_erro, erro], how="diagonal").drop_nulls().sort(cd.file_name)


        df_situacao = pl.read_excel(
        source = cd.CAMINHO_COD_SIT,
        engine = "openpyxl")

        df_cfop = pl.read_excel(
        source = cd.CAMINHO_CFOP,
        engine = "openpyxl")


        Fiscal, Contribuicoes = dr.process(df_contribuicoes, df_fiscal)

        Contribuicoes = Contribuicoes.select(cd.PERÍODO, cd.Registro, cd.CNPJ, pl.col(cd.DT_DOC).str.strptime(pl.Date, format="%d%m%Y"), 
                                        cd.NUM_DOC, cd.COD_MOD, cd.IND_OPER, cd.IND_ESCRI, pl.col(cd.CFOP).cast(pl.Int64), 
                                        cd.COD_SIT, cd.CST, cd.ALIQ, cd.VL_ITEM, cd.CHV_NFE)
        Contribuicoes = Contribuicoes.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO))
        
        ContribC100 = df_contribuicoes.filter((pl.col(cd.Registro) == 'C100'))
        ContribC100 = fr.renomear_colunas(ContribC100, cd.C_re_C100)
        ContribC100 = ContribC100.select([cd.CHV_NFE, cd.COD_PART, cd.COD_SIT])

        Contrib0150 = df_contribuicoes.filter((pl.col(cd.Registro) == '0150'))
        Contrib0150 = fr.renomear_colunas(Contrib0150, cd.C_re_0150)
        Contrib0150 = Contrib0150.select([cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART])

        Contribuicoes = Contrib0150.join(ContribC100, on=cd.COD_PART, how="right", coalesce=True 
                                ).join(Contribuicoes, on=cd.CHV_NFE, how="right", coalesce = True)

        Contribuicoes = Contribuicoes.join(df_situacao, left_on=cd.COD_SIT, right_on=cd.COD_SIT_DOC, how="left"
                                    ).join(df_cfop, on=cd.CFOP, how="left")
        
        Contribuicoes = (Contribuicoes.filter(pl.col(cd.COD_SIT) == "00")
                         ).drop_nulls(subset=[cd.CHV_NFE,cd.DESCRICAO])
        
        quebraContrib = Contribuicoes.remove(
        (pl.col(cd.CST).is_in(["01", "02", "03", "04", "05"])) & (pl.col(cd.ALIQ) == "0"))

        quebraContrib = quebraContrib.drop(cd.DESC_DOC, "Data de Fim", 
                                           "Data de Início", "COD_SIT_right", cd.ALIQ).unique()
        
        quebraContrib = quebraContrib.select(
                pl.col(cd.PERÍODO), pl.col(cd.Registro), pl.col(cd.CNPJ), pl.col(cd.COD_PART), pl.col(cd.NOME_DEST),
                pl.col(cd.CNPJ_DEST), pl.col(cd.NUM_DOC), pl.col(cd.CHV_NFE), pl.col(cd.DT_DOC), pl.col(cd.CST), 
                pl.col(cd.CFOP), pl.col(cd.DESCRICAO), pl.col(cd.COD_SIT), pl.col(cd.COD_MOD), pl.col(cd.IND_OPER), 
                pl.col(cd.IND_ESCRI), pl.col(cd.VL_ITEM), pl.col(cd.ANO)).sort([cd.PERÍODO, cd.VL_ITEM], descending=[False, True])


        Fiscal = Fiscal.select(cd.PERÍODO, cd.Registro, cd.CNPJ, cd.NUM_DOC, cd.CHV_NFE, pl.col(cd.DT_DOC).str.strptime(pl.Date, format="%d%m%Y"), 
                               cd.CST_ICMS, pl.col(cd.CFOP).cast(pl.Int64), cd.COD_SIT, cd.ALIQ_ICMS, cd.VL_OPR, cd.VL_BC_ICMS, cd.VL_ICMS, 
                               cd.VL_BC_ICMS_ST, cd.VL_ICMS_ST, cd.VL_IPI)
        
        Fiscal = Fiscal.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO))

        FiscalC100 = df_fiscal.filter((pl.col(cd.Registro) == 'C100'))
        FiscalC100 = fr.renomear_colunas(FiscalC100, cd.ICMS_re_C100)
        FiscalC100 = FiscalC100.select([cd.CHV_NFE, cd.COD_PART, cd.COD_SIT])

        Fiscal0150 = df_fiscal.filter((pl.col(cd.Registro) == '0150'))
        Fiscal0150 = fr.renomear_colunas(Fiscal0150, cd.ICMS_re_0150)
        Fiscal0150 = Fiscal0150.select([cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART])

        Fiscal = Fiscal0150.join(FiscalC100, on=cd.COD_PART, how="right", coalesce=True
                                 ).join(Fiscal, on=cd.CHV_NFE, how="right")
        Fiscal = Fiscal.join(df_situacao, left_on=cd.COD_SIT, right_on=cd.COD_SIT_DOC, how="left"
                        ).join(df_cfop, on=cd.CFOP, how="left")

        Fiscal = Fiscal.with_columns(
                pl.when(pl.col(cd.Registro) == "C190")
                .then((pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_ICMS_ST).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_IPI).str.replace(",", ".").cast(pl.Float64)).alias(cd.CALC_CONFRONTO))
                .otherwise(pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64).alias(cd.CALC_CONFRONTO))
                )
        
        Fiscal = (Fiscal.filter(pl.col(cd.COD_SIT) == "00")
                                ).drop_nulls(subset=[cd.CHV_NFE, cd.DESCRICAO]
                                ).unique()
        
        quebra_fiscal = Fiscal.select(
                pl.col(cd.PERÍODO), pl.col(cd.Registro), pl.col(cd.CNPJ), pl.col(cd.COD_PART), pl.col(cd.NOME_DEST),
                pl.col(cd.CNPJ_DEST), pl.col(cd.NUM_DOC), pl.col(cd.CHV_NFE), pl.col(cd.DT_DOC), pl.col(cd.CST_ICMS), 
                pl.col(cd.CFOP), pl.col(cd.DESCRICAO), pl.col(cd.COD_SIT), pl.col(cd.ALIQ_ICMS), pl.col(cd.VL_OPR),  pl.col(cd.VL_BC_ICMS), 
                pl.col(cd.VL_ICMS), pl.col(cd.VL_BC_ICMS_ST), pl.col(cd.VL_ICMS_ST), pl.col(cd.VL_IPI), pl.col(cd.CALC_CONFRONTO), pl.col(cd.ANO)
        ).sort([cd.PERÍODO, cd.CALC_CONFRONTO], descending=[False, True])

        
        cnpj_f = quebra_fiscal.select(cd.CNPJ).unique(subset=[cd.CNPJ], keep="first")
        cnpj_c = quebraContrib.select(cd.CNPJ).unique(subset=[cd.CNPJ], keep="first")
        verificacao_cnpj = cnpj_f.join(cnpj_c, on = cd.CNPJ, how="inner")
        

        NFe = df_nfe.join(df_cfop, on=cd.CFOP, how='left')

        NFe = NFe.join(verificacao_cnpj, on=cd.CNPJ, how="semi")

        NFe = NFe.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO),
                               pl.col(cd.PERÍODO).dt.replace(day=1).alias(cd.PERÍODO))
        
        NFe = NFe.with_columns(
                (pl.col(cd.vProd) - pl.col(cd.vDesc) + pl.col(cd.vFrete) 
                 + pl.col(cd.vSeg) + pl.col(cd.vOutro) - pl.col(cd.vICMSDeson)).alias(cd.CALC_CONFRONTO))

        quebra_nfe = NFe.select(
                pl.col(cd.nNF), pl.col(cd.PERÍODO), pl.col(cd.xMun_EMIT), pl.col(cd.xMun_DEST), pl.col(cd.CNPJ),
                pl.col(cd.NOME), pl.col(cd.CNPJ_DEST), pl.col(cd.NOME_DEST), pl.col(cd.CHV_NFE), pl.col(cd.CFOP),
                pl.col(cd.DESCRICAO), pl.col(cd.SITUACAO), pl.col(cd.vProd), pl.col(cd.vFrete), pl.col(cd.vSeg),
                pl.col(cd.vOutro), pl.col(cd.vICMSDeson), pl.col(cd.vDesc), pl.col(cd.CALC_CONFRONTO),pl.col(cd.ANO)                
        ).drop_nulls([pl.col(cd.nNF), pl.col(cd.DESCRICAO)]).filter(pl.col(cd.SITUACAO) == "Autorizado o uso NF-e"
        ).sort(cd.PERÍODO)


        Contribuicoes_select = Contribuicoes.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.Registro).alias("EFD_C"), pl.col(cd.VL_ITEM), pl.col(cd.DESC_DOC).alias("Desc_efdc"), pl.col(cd.ANO))

        Fiscal_select = Fiscal.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.Registro).alias("EFD_F"), pl.col(cd.CALC_CONFRONTO).alias(cd.VL_EFD_F), pl.col(cd.DESC_DOC).alias("Desc_efdf"), pl.col(cd.ANO))

        NFe_select = NFe.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.CALC_CONFRONTO).alias(cd.VL_NFE), pl.col(cd.ANO))


        df_analitico = Contribuicoes_select.join(Fiscal_select, on=[cd.CHV_NFE, cd.PERÍODO, cd.ANO], how="full", coalesce=True
        ).join(NFe_select, on=[cd.CHV_NFE, cd.PERÍODO, cd.ANO],how="full",coalesce=True)

        df_analitico = df_analitico.with_columns(
                pl.when(pl.col("EFD_C").is_null())
                .then(pl.col("Desc_efdc").alias("EFD_C"))
                .otherwise(pl.col("EFD_C").alias("EFD_C")),

                pl.when(pl.col("EFD_F").is_null())
                .then(pl.col("Desc_efdf").alias("EFD_F"))
                .otherwise(pl.col("EFD_F").alias("EFD_F")),
                
                pl.when(pl.col(cd.VL_NFE).is_null())
                .then(pl.lit(0).alias(cd.VL_NFE))
                .otherwise(pl.col(cd.VL_NFE).alias(cd.VL_NFE)),

                pl.when(pl.col(cd.VL_EFD_F).is_null())
                .then(pl.lit(0).alias(cd.VL_EFD_F))
                .otherwise(pl.col(cd.VL_EFD_F).alias(cd.VL_EFD_F)),

                pl.when(pl.col(cd.VL_ITEM).is_null())
                .then(pl.lit(0).alias(cd.VL_ITEM))
                .otherwise(pl.col(cd.VL_ITEM).alias(cd.VL_ITEM)))
        
        df_analitico = df_analitico.with_columns(
               (pl.col(cd.VL_NFE) - pl.col(cd.VL_ITEM)).alias("XML X ICMS"),
               (pl.col(cd.VL_NFE) - pl.col(cd.VL_EFD_F)).alias("XML X EFD"),
               (pl.col(cd.VL_EFD_F) - pl.col(cd.VL_ITEM)).alias("ICMS X EFD"))
        
        Analitico = df_analitico.with_columns(
        pl.col(cd.PERÍODO).dt.month().alias(cd.MES)
        )
        Analitico = Analitico.with_columns(
                pl.when(pl.col(cd.MES).is_in([1, 2, 3]))
                        .then(pl.lit("1º trimestre"))
                .when(pl.col(cd.MES).is_in([4, 5, 6]))
                        .then(pl.lit("2º trimestre"))
                .when(pl.col(cd.MES).is_in([7, 8, 9]))
                        .then(pl.lit("3º trimestre"))
                .when(pl.col(cd.MES).is_in([10, 11, 12]))
                        .then(pl.lit("4º trimestre"))
                .otherwise(pl.lit("0"))
                .alias("Trimestre"))

        Analitico = Analitico.select(
                pl.col(cd.PERÍODO), pl.col(cd.CHV_NFE), pl.col(cd.SITUACAO), pl.col(cd.VL_NFE), pl.col("EFD_F"), pl.col(cd.VL_EFD_F),
                pl.col("EFD_C"), pl.col(cd.VL_ITEM), pl.col("XML X ICMS"), pl.col("XML X EFD"), pl.col("ICMS X EFD"), pl.col("Trimestre")
        )


        nConsiderado = an.nConsiderado(NFe).sort(cd.PERÍODO)


        df_empresa = pl.concat([
                df_contribuicoes.select([cd.NOME, cd.CNPJ, cd.Registro]).filter(pl.col(cd.Registro) == '0000'),
                df_fiscal.select([cd.NOME, cd.CNPJ, cd.Registro]).filter(pl.col(cd.Registro) == '0000'),
                quebra_nfe.select([cd.NOME, cd.CNPJ])
                ], how="diagonal")
        empresa, cnpj = em.empresa_cnpj(inbound, df_empresa)

        
        # we.excel_receita(self, empresa, quebraContrib, quebra_fiscal, Notas, quebra_nfe, nConsiderado, nProcessado, Analico, projeto)