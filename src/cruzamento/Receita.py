import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd
import cruzamento.write_excel as we
import cruzamento.file_reader as fr
import cruzamento.analise as an
import cruzamento.empresa as em
import cruzamento.dados_receita as dr


def process_receita(inbound, df_contribuicoes, df_fiscal, self, projeto):

        NFe, xml_erro = dr.processXML(inbound)

        erro = an.count_arquivos(NFe, df_contribuicoes, df_fiscal, self)  
        xml = an.filtrar_fora_do_padrao(inbound, '.xml', pl.col(fd.IS_NFE), cd.status_xml)
        txt = an.filtrar_fora_do_padrao(inbound, '.txt', pl.col(fd.IS_EFDC) | pl.col(fd.IS_EFDF), cd.status_txt)

        nProcessado = pl.concat([xml, txt, xml_erro, erro], how="diagonal")


        df_empresa = pl.concat([
                df_contribuicoes.select([cd.NOME, cd.CNPJ, cd.Registro]).filter(pl.col(cd.Registro) == '0000'),
                df_fiscal.select([cd.NOME, cd.CNPJ, cd.Registro]).filter(pl.col(cd.Registro) == '0000'),
                NFe.select([cd.NOME_EMIT, cd.CNPJ_EMIT])
                ], how="diagonal")
        empresa, cnpj = em.empresa_cnpj(inbound, df_empresa)


        df_situacao = pl.read_excel(
        source = cd.CAMINHO_COD_SIT,
        engine = "openpyxl")

        df_cfop = pl.read_excel(
        source = cd.CAMINHO_CFOP,
        engine = "openpyxl")


        NFe = NFe.join(df_cfop, on=cd.CFOP, how='left')

        NFe = NFe.with_columns(pl.col(cd.PERÍODO).dt.year().alias(cd.ANO))
        
        NFe = NFe.with_columns(
                (pl.col(cd.vProd) - pl.col(cd.vDesc) + pl.col(cd.vFrete) 
                 + pl.col(cd.vSeg) + pl.col(cd.vOutro) - pl.col(cd.vICMSDeson)).alias(cd.CALC_CONFRONTO))
        
        nConsiderado = NFe.filter((pl.col(cd.DESCRICAO).is_null()) | (pl.col(cd.SITUACAO) != "Autorizado o uso da NF-e"))

        nConsiderado = nConsiderado.with_columns([
        pl.when(pl.col(cd.SITUACAO) == ("Autorizado o uso da NF-e"))
            .then(pl.lit("CFOP/CST não aplicáveis"))
        .otherwise(pl.lit("Nota cancelada"))
        .alias(cd.MOTIVO)  
    ])

        duplicados = NFe.filter(pl.col(cd.CHV_NFE).is_duplicated())
        duplicados = duplicados.with_columns([
                pl.lit("Nota fiscal eletrônica (NF-e) duplicada").alias(cd.MOTIVO)
        ])

        nConsiderado = pl.concat([duplicados, nConsiderado])
        nConsiderado = nConsiderado.select(pl.col(cd.nNF), pl.col(cd.PERÍODO), pl.col(cd.CHV_NFE), pl.col(cd.CFOP),
                                           pl.col(cd.DESCRICAO), pl.col(cd.SITUACAO), pl.col(cd.MOTIVO), pl.col(cd.vProd),
                                           pl.col(cd.vFrete), pl.col(cd.vSeg), pl.col(cd.vOutro), pl.col(cd.vDesc),
                                           pl.col(cd.vICMSDeson), pl.col(cd.CALC_CONFRONTO))

        quebra_nfe = NFe.select(
                pl.col(cd.nNF), pl.col(cd.PERÍODO), pl.col(cd.xMun_EMIT), pl.col(cd.xMun_DEST), pl.col(cd.CNPJ_EMIT),
                pl.col(cd.NOME_EMIT), pl.col(cd.CNPJ_DEST), pl.col(cd.NOME_DEST), pl.col(cd.CHV_NFE), pl.col(cd.CFOP),
                pl.col(cd.DESCRICAO), pl.col(cd.SITUACAO), pl.col(cd.vProd), pl.col(cd.vFrete), pl.col(cd.vSeg),
                pl.col(cd.vOutro), pl.col(cd.vICMSDeson), pl.col(cd.vDesc), pl.col(cd.CALC_CONFRONTO)                
        ).drop_nulls([pl.col(cd.nNF), pl.col(cd.DESCRICAO)]).filter(pl.col(cd.SITUACAO) == "Autorizado o uso da NF-e")

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

        Contribuicoes = Contribuicoes.join(df_situacao, left_on=cd.COD_SIT, right_on="Código da Situação do Documento", how="left"
                                    ).join(df_cfop, on=cd.CFOP, how="left")
        
        quebraContrib = (Contribuicoes.filter(pl.col(cd.COD_SIT) == "00")
                         ).drop_nulls(subset=[cd.CHV_NFE,cd.DESCRICAO])
        quebraContrib = quebraContrib.remove(
        (pl.col(cd.CST).is_in(["01", "02", "03", "04", "05"])) & (pl.col(cd.ALIQ) == "0"))
        quebraContrib = quebraContrib.drop("Descrição da Situação do Documento", "Data de Fim", 
                                           "Data de Início", "COD_SIT_right", cd.ALIQ).unique()
        
        quebraContrib = quebraContrib.select(
                pl.col(cd.PERÍODO), pl.col(cd.Registro), pl.col(cd.CNPJ), pl.col(cd.COD_PART), pl.col(cd.NOME_DEST),
                pl.col(cd.CNPJ_DEST), pl.col(cd.NUM_DOC), pl.col(cd.CHV_NFE), pl.col(cd.DT_DOC), pl.col(cd.CST), 
                pl.col(cd.CFOP), pl.col(cd.DESCRICAO), pl.col(cd.COD_SIT), pl.col(cd.COD_MOD), pl.col(cd.IND_OPER), 
                pl.col(cd.IND_ESCRI), pl.col(cd.VL_ITEM)
        )


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
        Fiscal = Fiscal.join(df_situacao, left_on=cd.COD_SIT, right_on="Código da Situação do Documento", how="left"
                        ).join(df_cfop, on=cd.CFOP, how="left")

        calculoConfronto_fiscal = Fiscal.with_columns(
                pl.when(pl.col(cd.Registro) == "C190")
                .then((pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_ICMS_ST).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_IPI).str.replace(",", ".").cast(pl.Float64)).alias(cd.CALC_CONFRONTO))
                .otherwise(pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64).alias(cd.CALC_CONFRONTO))
                ).drop("Descrição da Situação do Documento", "Data de Fim", "Data de Início", "COD_SIT_right")
        
        calculoConfronto_fiscal = (calculoConfronto_fiscal.filter(pl.col(cd.COD_SIT) == "00")
                                ).drop_nulls(subset=[cd.CHV_NFE,"Descrição"]).unique() 
        
        quebra_fiscal = calculoConfronto_fiscal.select(
                pl.col(cd.PERÍODO), pl.col(cd.Registro), pl.col(cd.CNPJ), pl.col(cd.COD_PART), pl.col(cd.NOME_DEST),
                pl.col(cd.CNPJ_DEST), pl.col(cd.NUM_DOC), pl.col(cd.CHV_NFE), pl.col(cd.DT_DOC), pl.col(cd.CST_ICMS), 
                pl.col(cd.CFOP), pl.col(cd.DESCRICAO), pl.col(cd.COD_SIT), pl.col(cd.ALIQ_ICMS), pl.col(cd.VL_OPR), 
                pl.col(cd.VL_BC_ICMS), pl.col(cd.VL_ICMS), pl.col(cd.VL_BC_ICMS_ST), pl.col(cd.VL_ICMS_ST), pl.col(cd.VL_IPI), pl.col(cd.CALC_CONFRONTO)
        )
        
        we.excel_receita(self, empresa, quebraContrib, quebra_fiscal, quebra_nfe, nConsiderado, nProcessado, projeto)