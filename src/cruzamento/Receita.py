import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.sped.sped_definitions as dfn
import cruzamento.file_reader as fr
import cruzamento.analise as an
import cruzamento.empresa as em
import cruzamento.dados_receita as dr


def process_receita(inbound, df_contribuicoes, df_fiscal, self):
        
        xml_erro = dr.processXML(inbound,)

        # NFe = df_nfe.unique(subset=[cd.nNF], keep="first")

        # analise = an.analise(df_nfe, xml_erro, df_contribuicoes, df_fiscal, self, inbound)

        df_situacao = pl.read_excel(
        source = cd.CAMINHO_COD_SIT,
        engine = "openpyxl")

        df_cfop = pl.read_excel(
        source = cd.CAMINHO_CFOP,
        engine = "openpyxl")


        Fiscal, Contribuicoes = dr.process(df_contribuicoes, df_fiscal)


        
        Contribuicoes = Contribuicoes.select(dfn.PERIODO, dfn.REGISTRO, dfn.CNPJ, pl.col(cd.DT_DOC).str.strptime(pl.Date, format="%d%m%Y"), 
                                        cd.NUM_DOC, cd.COD_MOD, cd.IND_OPER, cd.IND_ESCRI, pl.col(cd.CFOP).cast(pl.Int64), 
                                        cd.COD_SIT, cd.CST, cd.ALIQ, cd.VL_ITEM, cd.CHV_NFE)
        
        ContribC100 = df_contribuicoes.filter((pl.col(dfn.REGISTRO) == 'C100'))
        ContribC100 = fr.renomear_colunas(ContribC100, cd.C_re_C100)
        ContribC100 = ContribC100.select([cd.CHV_NFE, cd.COD_PART, cd.COD_SIT])

        Contrib0150 = df_contribuicoes.filter((pl.col(dfn.REGISTRO) == '0150'))
        Contrib0150 = fr.renomear_colunas(Contrib0150, cd.C_re_0150)
        Contrib0150 = Contrib0150.select([cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART])


        Contribuicoes = Contrib0150.join(ContribC100, on=cd.COD_PART, how="right", coalesce=True 
                                ).join(Contribuicoes, on=cd.CHV_NFE, how="right", coalesce = True)

        Contribuicoes = Contribuicoes.join(df_situacao, left_on=cd.COD_SIT, right_on="Código da Situação do Documento", how="left"
                                    ).join(df_cfop, on=cd.CFOP, how="left")
        
        
        quebraContrib = (Contribuicoes.filter(pl.col(cd.COD_SIT) == "00")
                         ).drop_nulls(subset=[cd.CHV_NFE,"Descrição"])
        quebraContrib = quebraContrib.remove(
        (pl.col(cd.CST).is_in(["01", "02", "03", "04", "05"])) & (pl.col(cd.ALIQ) == "0"))
        quebraContrib = quebraContrib.drop("Descrição da Situação do Documento", "Data de Fim", 
                                           "Data de Início", "COD_SIT_right", cd.ALIQ).unique()


        Fiscal = Fiscal.select(dfn.PERIODO, dfn.REGISTRO, dfn.CNPJ, cd.NUM_DOC, cd.CHV_NFE, pl.col(cd.DT_DOC).str.strptime(pl.Date, format="%d%m%Y"), 
                               cd.CST_ICMS, pl.col(cd.CFOP).cast(pl.Int64), cd.COD_SIT, cd.ALIQ_ICMS, cd.VL_OPR, cd.VL_BC_ICMS, cd.VL_ICMS, 
                               cd.VL_BC_ICMS_ST, cd.VL_ICMS_ST, cd.VL_IPI)

        FiscalC100 = df_fiscal.filter((pl.col(dfn.REGISTRO) == 'C100'))
        FiscalC100 = fr.renomear_colunas(FiscalC100, cd.ICMS_re_C100)
        FiscalC100 = FiscalC100.select([cd.CHV_NFE, cd.COD_PART, cd.COD_SIT])

        Fiscal0150 = df_fiscal.filter((pl.col(dfn.REGISTRO) == '0150'))
        Fiscal0150 = fr.renomear_colunas(Fiscal0150, cd.ICMS_re_0150)
        Fiscal0150 = Fiscal0150.select([cd.NOME_DEST, cd.CNPJ_DEST, cd.COD_PART])

        Fiscal = Fiscal0150.join(FiscalC100, on=cd.COD_PART, how="right", coalesce=True
                                 ).join(Fiscal, on=cd.CHV_NFE, how="right")
        Fiscal = Fiscal.join(df_situacao, left_on=cd.COD_SIT, right_on="Código da Situação do Documento", how="left"
                        ).join(df_cfop, on=cd.CFOP, how="left")

        calculoConfronto_fiscal = Fiscal.with_columns(
                pl.when(pl.col(dfn.REGISTRO) == "C190")
                .then(pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_ICMS_ST).str.replace(",", ".").cast(pl.Float64)
                        - pl.col(cd.VL_IPI).str.replace(",", ".").cast(pl.Float64))
                .otherwise(pl.col(cd.VL_OPR).str.replace(",", ".").cast(pl.Float64).alias("Calculo Confronto"))
                ).drop("Descrição da Situação do Documento", "Data de Fim", "Data de Início", "COD_SIT_right")
        calculoConfronto_fiscal = (calculoConfronto_fiscal.filter(pl.col(cd.COD_SIT) == "00")
                                ).drop_nulls(subset=[cd.CHV_NFE,"Descrição"]).unique() 
        

        df_empresa = pl.concat([
                df_contribuicoes.select([cd.NOME, cd.CNPJ, dfn.REGISTRO]).filter(pl.col(dfn.REGISTRO) == '0000'),
                df_fiscal.select([cd.NOME, cd.CNPJ, dfn.REGISTRO]).filter(pl.col(dfn.REGISTRO) == '0000')
                # ,df_nfe.select([cd.NOME, cd.CNPJ])
                ], how="diagonal")
        empresa = em.empresa_cnpj(inbound, df_empresa)
        
        
        # we.excel_receita(empresa, quebraContrib, calculoConfronto_fiscal, analise)