import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd
import cruzamento.write_excel as we
import cruzamento.analise as an
import cruzamento.empresa as em
import cruzamento.dados_receita as dr
import cruzamento.filtro_contr as fc
import cruzamento.file_reader as fr


def process_receita(inbound, df_contribuicoes, df_fiscal, self, projeto, path_env):

        df_nfe, xml_erro = dr.processXML(inbound)

        erro = an.count_arquivos(df_nfe, df_contribuicoes, df_fiscal, self)  
        xml = an.filtrar_fora_do_padrao(inbound, '.xml', pl.col(fd.IS_NFE), cd.status_xml)
        txt = an.filtrar_fora_do_padrao(inbound, '.txt', pl.col(fd.IS_EFDC) | pl.col(fd.IS_EFDF), cd.status_txt)
        nProcessado = pl.concat([xml, txt, xml_erro, erro], how="diagonal").drop_nulls().sort(cd.file_name)


        df_situacao = pl.read_excel(
        source = cd.CAMINHO_COD_SIT,
        engine = "openpyxl")

        df_cfop = pl.read_excel(
        source = cd.CAMINHO_XML_CFOP,
        engine = "openpyxl")


        fiscal, contribuicoes = dr.process_sped(df_contribuicoes, df_fiscal, path_env)


        contribuicoes = contribuicoes.select(cd.PERÍODO, cd.CHV_NFE, cd.Registro, cd.CNPJ, pl.col(cd.DT_DOC).str.strptime(pl.Date, format="%d%m%Y"), 
                                        cd.NUM_DOC, cd.COD_MOD, cd.IND_OPER, cd.IND_ESCRI, pl.col(cd.CFOP).cast(pl.Int64), 
                                        cd.COD_SIT, cd.CST, cd.ALIQ, pl.col(cd.VL_ITEM).str.replace(",", ".").cast(pl.Float64))
        
        
        contribuicoes = contribuicoes.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO))
        contribuicoes1 = contribuicoes.join(df_situacao, left_on=cd.COD_SIT, right_on=cd.COD_SIT_DOC, how="inner")
        contribuicoes1 = (contribuicoes1.filter(pl.col(cd.COD_SIT) == "00"))
        contribuicoes2 = contribuicoes.join(df_situacao, left_on=cd.COD_SIT, right_on=cd.COD_SIT_DOC, how="anti")
        contribuicoes = pl.concat([contribuicoes1, contribuicoes2], how="diagonal")

        ContribC100 = df_contribuicoes.filter((pl.col(cd.Registro) == 'C100'))
        ContribC100 = ContribC100.select([cd.CHV_NFE, cd.COD_PART, cd.COD_SIT]).filter(pl.col(cd.CHV_NFE) != "")

        Contrib0150 = df_contribuicoes.filter((pl.col(cd.Registro) == '0150'))
        Contrib0150 = Contrib0150.select([cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART]).group_by(cd.COD_PART).last()

        Contribuicoes = Contrib0150.join(ContribC100, on=cd.COD_PART, how="right", coalesce=True )
       

        Contribuicoes = Contribuicoes.join(contribuicoes, on=cd.CHV_NFE, how="full", coalesce = True)

        Contribuicoes = Contribuicoes.join(df_cfop, on=cd.CFOP, how="left")

        contribuicoes_desc = Contribuicoes.select(cd.CHV_NFE, pl.col(cd.DESC_DOC).alias("Desc_efdc")).group_by([cd.CHV_NFE, "Desc_efdc"]).all()
        

        cfop_vazio = Contribuicoes.filter(pl.col(cd.CFOP).is_null())
        df_limpo = Contribuicoes.filter(pl.col(cd.CFOP).is_not_null())
        Contribuicoes = pl.concat([df_limpo.filter(pl.col(cd.DESCRICAO).is_not_null() & (pl.col(cd.DESCRICAO) != "")),cfop_vazio])
       
        quebraContrib = Contribuicoes.remove(
        (pl.col(cd.CST).is_in(["01", "02", "03", "04", "05"])) & (pl.col(cd.ALIQ) == "0"))
        

        quebraContrib = fc.filtro_contribuicoes(quebraContrib)


        quebraContrib = quebraContrib.drop(cd.DESC_DOC, "Data de Fim", 
                                           "Data de Início", "COD_SIT_right", cd.ALIQ)
        
        quebraContrib = quebraContrib.select(
                pl.col(cd.PERÍODO), pl.col(cd.Registro), pl.col(cd.CNPJ), pl.col(cd.COD_PART), pl.col(cd.NOME_DEST),
                pl.col(cd.CNPJ_DEST), pl.col(cd.NUM_DOC), pl.col(cd.CHV_NFE), pl.col(cd.DT_DOC).dt.strftime("%d/%m/%Y"), pl.col(cd.CST), 
                pl.col(cd.CFOP), pl.col(cd.DESCRICAO), pl.col(cd.COD_SIT), pl.col(cd.COD_MOD), pl.col(cd.IND_OPER), 
                pl.col(cd.IND_ESCRI), pl.col(cd.VL_ITEM), pl.col(cd.ANO)).sort([cd.PERÍODO, cd.VL_ITEM], descending=[False, True])


        fiscal = fiscal.select(cd.PERÍODO, cd.Registro, cd.CNPJ, cd.NUM_DOC, cd.CHV_NFE, pl.col(cd.DT_DOC).str.strptime(pl.Date, format="%d%m%Y"), 
                               cd.CST_ICMS, pl.col(cd.CFOP).cast(pl.Int64), cd.COD_SIT, cd.ALIQ_ICMS, cd.VL_OPR, cd.VL_BC_ICMS, cd.VL_ICMS, 
                               cd.VL_BC_ICMS_ST, cd.VL_ICMS_ST, cd.VL_IPI)
        
        fiscal = fiscal.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO))

        FiscalC100 = df_fiscal.filter((pl.col(cd.Registro) == 'C100'))
        FiscalC100 = FiscalC100.select([cd.CHV_NFE, cd.COD_PART, cd.COD_SIT])

        Fiscal0150 = df_fiscal.filter((pl.col(cd.Registro) == '0150'))
        Fiscal0150 = Fiscal0150.select([cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART])

        Fiscal = Fiscal0150.join(FiscalC100, on=cd.COD_PART, how="full", coalesce=True)
        Fiscal = Fiscal.join(fiscal, on=cd.CHV_NFE, how="full")
        Fiscal = Fiscal.join(df_situacao, left_on=cd.COD_SIT, right_on=cd.COD_SIT_DOC, how="left"
                        ).join(df_cfop, on=cd.CFOP, how="left")
        fiscal_desc = Fiscal.select(cd.CHV_NFE, pl.col(cd.DESC_DOC).alias("Desc_efdf")).group_by([cd.CHV_NFE, "Desc_efdf"]).all()
        Fiscal = Fiscal.with_columns(
                pl.when(pl.col(cd.Registro) == "C190")
                .then((pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_ICMS_ST).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_IPI).str.replace(",", ".").cast(pl.Float64)).alias(cd.CALC_CONFRONTO))
                .otherwise(pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64).alias(cd.CALC_CONFRONTO))
                )
        
        Fiscal = (Fiscal.filter(pl.col(cd.COD_SIT) == "00")
                                ).drop_nulls(subset=[cd.CHV_NFE, cd.DESCRICAO]
                                )
        
        quebra_fiscal = Fiscal.select(
                pl.col(cd.PERÍODO), pl.col(cd.Registro), pl.col(cd.CNPJ), pl.col(cd.COD_PART), pl.col(cd.NOME_DEST),
                pl.col(cd.CNPJ_DEST), pl.col(cd.NUM_DOC), pl.col(cd.CHV_NFE), pl.col(cd.DT_DOC).dt.strftime("%d/%m/%Y"), pl.col(cd.CST_ICMS), 
                pl.col(cd.CFOP), pl.col(cd.DESCRICAO), pl.col(cd.COD_SIT), pl.col(cd.ALIQ_ICMS), pl.col(cd.VL_OPR),  pl.col(cd.VL_BC_ICMS), 
                pl.col(cd.VL_ICMS), pl.col(cd.VL_BC_ICMS_ST), pl.col(cd.VL_ICMS_ST), pl.col(cd.VL_IPI), pl.col(cd.CALC_CONFRONTO), pl.col(cd.ANO)
        ).sort([cd.PERÍODO, cd.CALC_CONFRONTO], descending=[False, True])

        
        cnpj_f = quebra_fiscal.select(cd.CNPJ).unique(subset=[cd.CNPJ], keep="first")
        cnpj_c = quebraContrib.select(cd.CNPJ).unique(subset=[cd.CNPJ], keep="first")
        verificacao_cnpj = cnpj_f.join(cnpj_c, on = cd.CNPJ, how="inner")

        
        NFe = df_nfe.join(df_cfop, on=cd.CFOP, how='left')
        

        NFe = NFe.with_columns(
                (pl.col(cd.vProd) - pl.col(cd.vDesc) + pl.col(cd.vFrete) 
                 + pl.col(cd.vSeg) + pl.col(cd.vOutro) - pl.col(cd.vICMSDeson)).alias(cd.CALC_CONFRONTO))


        NFe = NFe.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO),
                               pl.col(cd.PERÍODO).dt.replace(day=1).alias(cd.PERÍODO))
        
        quebra_nfe = NFe.filter(pl.col(cd.SITUACAO) == "Autorizado o uso da NF-e" )
        
        quebra_nfe = quebra_nfe.drop_nulls(pl.col(cd.DESCRICAO))

        quebra_nfe = quebra_nfe.join(verificacao_cnpj, left_on=cd.CNPJ_DEST, right_on=cd.CNPJ, how="anti")

        quebra_nfe = quebra_nfe.select(
                pl.col(cd.nNF), pl.col(cd.PERÍODO), pl.col(cd.xMun_EMIT), pl.col(cd.xMun_DEST), pl.col(cd.CNPJ),
                pl.col(cd.NOME), pl.col(cd.CNPJ_DEST), pl.col(cd.NOME_DEST), pl.col(cd.CHV_NFE), pl.col(cd.CFOP),
                pl.col(cd.DESCRICAO), pl.col(cd.SITUACAO), pl.col(cd.vProd), pl.col(cd.vFrete), pl.col(cd.vSeg),
                pl.col(cd.vOutro), pl.col(cd.vICMSDeson), pl.col(cd.vDesc), pl.col(cd.CALC_CONFRONTO),pl.col(cd.ANO)                
        ).sort(cd.PERÍODO)
        
        analitico = pl.concat([quebraContrib, quebra_fiscal, quebra_nfe], how="diagonal")
        analitico = analitico.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.ANO))
        analitico = analitico.group_by([cd.CHV_NFE,cd.PERÍODO,cd.ANO]).all()


        Contribuicoes_select = quebraContrib.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.Registro).alias(cd.EFD_CONTRIBUICOES), 
                                                    pl.col(cd.VL_ITEM), pl.col(cd.ANO), pl.col(cd.NOME_DEST), pl.col(cd.CNPJ_DEST), pl.col(cd.COD_PART))
        Contribuicoes_select = Contribuicoes_select.group_by([cd.CHV_NFE, cd.EFD_CONTRIBUICOES, cd.PERÍODO, cd.ANO, cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART]).agg(pl.col(cd.VL_ITEM).sum().round(2))
        
        
        Fiscal_select = quebra_fiscal.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.Registro).alias(cd.EFD_ICMS_IPI), pl.col(cd.CALC_CONFRONTO).alias(cd.VL_EFD_F), pl.col(cd.ANO),pl.col(cd.NOME_DEST), pl.col(cd.CNPJ_DEST), pl.col(cd.COD_PART))
        Fiscal_select = Fiscal_select.group_by([cd.CHV_NFE, cd.EFD_ICMS_IPI, cd.PERÍODO, cd.ANO, cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART]).agg(pl.col(cd.VL_EFD_F).sum().round(2))
        
        NFe_select = quebra_nfe.select(pl.col(cd.CHV_NFE), pl.col(cd.PERÍODO), pl.col(cd.CALC_CONFRONTO).alias(cd.VL_NFE), pl.col(cd.SITUACAO), pl.col(cd.ANO), pl.col(cd.NOME_DEST), pl.col(cd.CNPJ_DEST),pl.lit("SIM").alias(cd.NFe))
        NFe_select = NFe_select.group_by([cd.CHV_NFE, cd.SITUACAO, cd.PERÍODO, cd.ANO, cd.NOME_DEST, cd.CNPJ_DEST, cd.NFe]).agg(pl.col(cd.VL_NFE).sum().round(2))
       

        analitico = analitico.join(Contribuicoes_select, on=[cd.CHV_NFE, cd.PERÍODO, cd.ANO], how="left", nulls_equal=True, coalesce=True, suffix="_contib"
        ).join(Fiscal_select, on=[cd.CHV_NFE, cd.PERÍODO, cd.ANO], how="left", coalesce=True, suffix="_fiscal"
        ).join(NFe_select, on=[cd.CHV_NFE, cd.PERÍODO, cd.ANO], how="left", coalesce=True, suffix="_nfe")

        
        df_analitico = analitico.join(fiscal_desc, on=cd.CHV_NFE, how = "left", coalesce=True
                                ).join(contribuicoes_desc, on=cd.CHV_NFE, how="left", coalesce=True)
        
        df_analitico = df_analitico.with_columns(
                pl.when(pl.col(cd.EFD_CONTRIBUICOES).is_null())
                .then(pl.col("Desc_efdc").alias(cd.EFD_CONTRIBUICOES))
                .otherwise(pl.col(cd.EFD_CONTRIBUICOES).alias(cd.EFD_CONTRIBUICOES)),

                pl.when(pl.col(cd.EFD_ICMS_IPI).is_null())
                .then(pl.col("Desc_efdf").alias(cd.EFD_ICMS_IPI))
                .otherwise(pl.col(cd.EFD_ICMS_IPI).alias(cd.EFD_ICMS_IPI)),
                
                pl.when(pl.col(cd.VL_NFE).is_null())
                .then(pl.lit(0).alias(cd.VL_NFE))
                .otherwise(pl.col(cd.VL_NFE).alias(cd.VL_NFE)),

                pl.when(pl.col(cd.VL_EFD_F).is_null())
                .then(pl.lit(0).alias(cd.VL_EFD_F))
                .otherwise(pl.col(cd.VL_EFD_F).alias(cd.VL_EFD_F)),

                pl.when(pl.col(cd.VL_ITEM).is_null())
                .then(pl.lit(0).alias(cd.VL_ITEM))
                .otherwise(pl.col(cd.VL_ITEM).alias(cd.VL_ITEM)))
        

        Analitico = df_analitico.with_columns(
               (pl.col(cd.VL_NFE) - pl.col(cd.VL_ITEM)).alias("XML X ICMS"),
               (pl.col(cd.VL_NFE) - pl.col(cd.VL_EFD_F)).alias("XML X EFD"),
               (pl.col(cd.VL_EFD_F) - pl.col(cd.VL_ITEM)).alias("ICMS X EFD"))
        
        Analitico = Analitico.with_columns(pl.col(cd.PERÍODO).dt.month().alias(cd.MES))

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
                .alias(cd.TRIMESTRE))

        Confronto_Analitico = Analitico.select(
                pl.col(cd.PERÍODO), pl.col(cd.CHV_NFE), pl.col(cd.SITUACAO), pl.col(cd.VL_NFE), pl.col(cd.EFD_ICMS_IPI), pl.col(cd.VL_EFD_F),
                pl.col(cd.EFD_CONTRIBUICOES), pl.col(cd.VL_ITEM), pl.col("XML X ICMS"), pl.col("XML X EFD"), pl.col("ICMS X EFD"), pl.col(cd.TRIMESTRE), pl.col(cd.ANO))


        nConsiderado = an.nConsiderado(NFe).sort(cd.PERÍODO)

        tot_nConsiderado = nConsiderado.group_by(cd.ANO).agg(pl.len().alias("total_nConsiderado"))
        analitico = analitico.drop_nulls(subset = cd.CHV_NFE)

        total = analitico.group_by([cd.ANO]).agg(pl.len().alias("TOTAL"))
        
        diferenca = Analitico.with_columns(
                pl.when((pl.col("XML X ICMS") != 0 )| (pl.col("XML X EFD")!= 0) | (pl.col("ICMS X EFD")!= 0))
                .then(1).alias("Diferença")
        )
        
        diferenca = diferenca.join(total, on=cd.ANO, how="full", coalesce=True
                        ).join(tot_nConsiderado, on=cd.ANO, how="full", coalesce=True)

        Notas = analitico.join(diferenca, on=[cd.ANO,cd.CHV_NFE], how="inner", coalesce=True)

        Notas = Notas.with_columns(
                pl.when(pl.col(cd.EFD_CONTRIBUICOES).is_null())
                .then(pl.lit("Não"))
                .otherwise (pl.lit("Sim"))
                .alias(cd.EFD_CONTRIBUICOES),

                pl.when(pl.col(cd.EFD_ICMS_IPI).is_null())
                .then(pl.lit("Não"))
                .otherwise (pl.lit("Sim"))
                .alias(cd.EFD_ICMS_IPI),

                pl.when(pl.col(cd.NFe).is_null())
                .then(pl.lit("Não"))
                .otherwise (pl.col(cd.NFe))
                .alias(cd.NFe)
        )

        Notas = Notas.with_columns([
        pl.coalesce([pl.col("COD_PART_fiscal"), pl.col(cd.COD_PART)]).alias(cd.COD_PART),
        pl.coalesce([pl.col(cd.CNPJ_DEST), pl.col("CNPJ_fiscal"), pl.col("CNPJ_nfe")]).alias(cd.CNPJ_DEST),
        pl.coalesce([pl.col(cd.NOME_DEST), pl.col("NOME_DEST_fiscal"), pl.col("NOME_DEST_nfe")]).alias(cd.NOME_DEST)
        ])

        Notas = Notas.select(pl.col(cd.PERÍODO), pl.col(cd.CHV_NFE), pl.col(cd.COD_PART), pl.col(cd.CNPJ_DEST), pl.col(cd.NOME_DEST), 
                             pl.col(cd.EFD_ICMS_IPI),pl.col(cd.EFD_CONTRIBUICOES),pl.col(cd.NFe), pl.col("TOTAL"), pl.col("Diferença"), 
                             pl.col("total_nConsiderado"), pl.col(cd.ANO)).sort(cd.PERÍODO, descending=False)


        # consolidado
        Consolidado = Confronto_Analitico.select(cd.PERÍODO, cd.ANO, cd.CHV_NFE).group_by([cd.PERÍODO, cd.ANO]).all().sort(cd.PERÍODO)
        Consolidado = Consolidado.with_columns((pl.cum_count(cd.CHV_NFE).over(cd.ANO) + 11).alias(cd.linha))
        Consolidado = Consolidado.drop(cd.CHV_NFE)
        
        Confronto_Consolidado = Consolidado.with_columns([
                pl.format("=SUMIF('CONFRONTO - ANALITICO'!B12:B1000000,B{},'CONFRONTO - ANALITICO'!E12:E1000000)", pl.col(cd.linha)).alias(cd.VL_NFE),
                pl.format("=SUMIF('CONFRONTO - ANALITICO'!B12:B1000000,B{},'CONFRONTO - ANALITICO'!G12:G1000000)", pl.col(cd.linha)).alias(cd.VL_EFD_F),
                pl.format("=SUMIF('CONFRONTO - ANALITICO'!B12:B1000000,B{},'CONFRONTO - ANALITICO'!I12:I1000000)", pl.col(cd.linha)).alias(cd.VL_ITEM),
                pl.format("=C{}-D{}", pl.col(cd.linha), pl.col(cd.linha)).alias("XML x ICMS"),
                pl.format("=C{}-E{}", pl.col(cd.linha), pl.col(cd.linha)).alias("XML x CONTRIB"),
                pl.format("=D{}-E{}", pl.col(cd.linha), pl.col(cd.linha)).alias("ICMS x CONTRIB")
        ])


        # anual
        Anual = Confronto_Analitico.select(cd.ANO).group_by(cd.ANO).all()
        Anual = Anual.with_columns([
                pl.lit("='CONFRONTO - ANALITICO'!E9").alias(cd.VL_NFE),
                pl.lit("='CONFRONTO - ANALITICO'!G9").alias(cd.VL_EFD_F),
                pl.lit("='CONFRONTO - ANALITICO'!I9").alias(cd.VL_ITEM),
                pl.lit("=C12-D12").alias("XML x ICMS"),
                pl.lit("=C12-E12").alias("XML x CONTRIB"),
                pl.lit("=D12-E12").alias("ICMS x CONTRIB")  
        ])


        # trimestal
        Trimestral = Confronto_Analitico.select(cd.ANO, cd.TRIMESTRE, cd.CHV_NFE).group_by(cd.ANO, cd.TRIMESTRE).all().sort(cd.ANO, cd.TRIMESTRE)
        
        Trimestral = Trimestral.with_columns((pl.cum_count(cd.CHV_NFE).over(cd.ANO) + 11).alias(cd.linha))
        Trimestral = Trimestral.drop(cd.CHV_NFE)
        
        Trimestral = Trimestral.with_columns([
                pl.format("=SUMIF('CONFRONTO - ANALITICO'!M12:M1000000,C{},'CONFRONTO - ANALITICO'!E12:E1000000)", pl.col(cd.linha)).alias(cd.VL_NFE),
                pl.format("=SUMIF('CONFRONTO - ANALITICO'!M12:M1000000,C{},'CONFRONTO - ANALITICO'!G12:G1000000)", pl.col(cd.linha)).alias(cd.VL_EFD_F),
                pl.format("=SUMIF('CONFRONTO - ANALITICO'!M12:M1000000,C{},'CONFRONTO - ANALITICO'!I12:I1000000)", pl.col(cd.linha)).alias(cd.VL_ITEM),
                pl.format("=D{}-E{}", pl.col(cd.linha), pl.col(cd.linha)).alias("XML x ICMS"),
                pl.format("=D{}-F{}", pl.col(cd.linha), pl.col(cd.linha)).alias("XML x CONTRIB"),
                pl.format("=E{}-F{}", pl.col(cd.linha), pl.col(cd.linha)).alias("ICMS x CONTRIB")
        ])


        empresa, cnpj = em.empresa_cnpj(inbound, df_fiscal, df_contribuicoes)

        
        we.excel_receita(self, empresa, quebraContrib, quebra_fiscal, Notas, quebra_nfe, nConsiderado, nProcessado, Anual, Trimestral, Confronto_Consolidado, Confronto_Analitico, projeto)