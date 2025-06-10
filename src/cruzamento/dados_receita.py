import polars as pl
from polars import DataFrame
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
import datatricks.sped.conversor_sped as cv
import cruzamento.file_reader as fr
import datatricks.io.file_definitions as fd


def rename_with_suffix(list:list) -> list:
        """Description: 
            Insert a -n suffix on repeated terms on a list
        Parameters:
            List - a list you want to apply a suffix
        Return: 
            A list with a id suffix on repetead terms
        """
        seen = {}
        result = []
        for item in list:
            if item in seen:
                seen[item] += 1
                result.append(f"{item}{seen[item]}")
            else:
                seen[item] = 1
                result.append(item)
        return result


def rename_columns(df:DataFrame, asset:DataFrame, version:str, register:str) -> DataFrame:
        """Renomeia colunas do dataframe
        df: df com colunas que serão renomeadas
        asset: df com novos nomes das colunas 
        version: versão do sped
        register: registro das colunas
        """
        colunas_fixas = [dfn.PERIODO, dfn.REGISTRO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI, dfn.ID_REG, dfn.VERSAO]
        asset = asset.filter((pl.col(dfn.VERSAO) == version) & (pl.col(dfn.REGISTRO) == register))
        asset = asset.select(dfn.CAMPO).to_series().to_list()
        asset = rename_with_suffix(asset)
        colunas_fixas.extend(asset)
        new_column_name = colunas_fixas
        old_columns = df.columns
        colunas_faltantes = len(old_columns) - len(new_column_name)
        new_column_name.extend([f'field_{i}' for i in range(0, colunas_faltantes)])
        columns = dict(zip(old_columns, new_column_name))
        df = df.rename(columns)
        columns = df.columns
        cols_to_drop = [col for col in columns if col.startswith('field_')]
        df = df.drop(cols_to_drop)
        return df
def processXML(inbound):
    regex_list = [
    r'^(nfeProc_NFe_infNFe_det_)(\d+_)*prod_CFOP$',
    r'^(nfeProc_NFe_infNFe_det_)(\d+_)*prod_vProd$'
]
    df_nfe, xml_erro = fr.leitor_nfe(inbound, fd.IS_NFE, cd.status_xml, regex_list, rename=cd.NFE[cd.rename_r],field_list=cd.NFE[cd.CAMPOS_RECEITA] )

    df_nfe = df_nfe.select(pl.col(cd.CHV_NFE), pl.col(*regex_list))

    
    df_long = df_nfe.unpivot( index=[cd.CHV_NFE])


    df_long = df_long.with_columns(
        pl.col("variable").str.extract(r"_(\d+)_", 1).cast(pl.Int64).alias("NItem"),
        pl.col("variable").str.replace(r"det_\d+_", "det_").alias("novo_campo")
    )

    df_long= df_long.pivot("novo_campo", index=[cd.CHV_NFE, "NItem"], values="value")

    
    return  xml_erro
        

def process(df_contribuicoes, df_fiscal):
    
        df_json = pl.read_json(cd.json_path)
        lista_contr = df_json.get_column("Registros_contri")
        Contribuicoes = df_contribuicoes.filter(pl.col("Registro").is_in(lista_contr))
        version_c = df_contribuicoes.select(pl.col(dfn.VERSAO))[0].item()
        df_assets_c = cv.get_remote_assets(dfn.EFDC)

        F500 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'F500')
        f500 = rename_columns(F500, df_assets_c, version_c, 'F500')
        
        F550 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'F550')
        f550 = rename_columns(F550, df_assets_c, version_c, 'F550')

        C170 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C170')
        c170 = rename_columns(C170, df_assets_c, version_c, 'C170')

        C870 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C870')
        c870 = rename_columns(C870, df_assets_c, version_c, 'C870')

        C601 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C601')
        c601 = rename_columns(C601, df_assets_c, version_c, 'C601')

        F100 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'F100')
        f100 = rename_columns(F100, df_assets_c, version_c, 'F100')

        F510 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'F510')
        f510 = rename_columns(F510, df_assets_c, version_c, 'F510')

        F200 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'F200')
        f200 = rename_columns(F200, df_assets_c, version_c, 'F200')

        C481 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C481')
        c481 = rename_columns(C481, df_assets_c, version_c, 'C481')

        A170 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'A170')
        a170 = rename_columns(A170, df_assets_c, version_c, 'A170')

        D201 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'D201')
        d201 = rename_columns(D201, df_assets_c, version_c, 'D201')

        C381 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C381')
        c381 = rename_columns(C381, df_assets_c, version_c, 'C381')

        C491 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C491')
        c491 = rename_columns(C491, df_assets_c, version_c, 'C491')

        C175 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C175')
        c175 = rename_columns(C175, df_assets_c, version_c, 'C175')

        D601 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'D601')
        d601 = rename_columns(D601, df_assets_c, version_c, 'D601')

        F560 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'F560')
        f560 = rename_columns(F560, df_assets_c, version_c, 'F560')

        D350 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'D350')
        d350 = rename_columns(D350, df_assets_c, version_c, 'D350')

        D300 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'D300')
        d300 = rename_columns(D300, df_assets_c, version_c, 'D300')

        C181 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C181')
        c181 = rename_columns(C181, df_assets_c, version_c, 'C181')

        C880 = Contribuicoes.filter(pl.col(dfn.REGISTRO) == 'C880')
        c880 = rename_columns(C880, df_assets_c, version_c, 'C880')

        Contribuicoes = pl.concat([a170, c170, c175, c181, c381, c481, c491, c601, c870, c880, d201, 
                                   d300, d350, d601, f100, f200, f500, f510, f550, f560], how="diagonal")
        
        df_cont_renomeado = Contribuicoes.with_columns(
            pl.coalesce([pl.col(cd.VL_ITEM), pl.col("VL_REC_COMP"), pl.col("VL_REC_CAIXA"), pl.col("VL_TOT_REC"), 
                         pl.col("VL_BRT"), pl.col("VL_DOC"), pl.col("VL_OPER"), pl.col("VL_OPR") ]).alias(cd.VL_ITEM),
            pl.coalesce([pl.col("CST_COFINS"), pl.col("CST_PIS")]).alias("CST"),
            pl.coalesce([pl.col("DT_OPER"), pl.col("DT_REF"), pl.col("DT_DOC_INI"), pl.col(cd.DT_DOC)]).alias(cd.DT_DOC),
            pl.coalesce([pl.col("NUM_DOC_INI"), pl.col(cd.NUM_DOC)]).alias(cd.NUM_DOC),
            pl.coalesce([pl.col("COD_SIT;"), pl.col(cd.COD_SIT)]).alias(cd.COD_SIT),
            pl.coalesce([pl.col("ALIQ_PIS"), pl.col("ALIQ_COFINS")]).alias(cd.ALIQ)
            )
        
        lista_fiscal = df_json.get_column("Registros_fiscal")
        Fiscal = df_fiscal.filter(pl.col("Registro").is_in(lista_fiscal))
        version_f = df_fiscal.select(pl.col(dfn.VERSAO))[0].item()
        df_assets_f = cv.get_remote_assets(dfn.EFDF)


        C490 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C490')
        c490 = rename_columns(C490, df_assets_f, version_f, 'C490')

        D190 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D190')
        d190 = rename_columns(D190, df_assets_f, version_f, 'D190')

        C190 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C190')
        c190 = rename_columns(C190, df_assets_f, version_f, 'C190')

        D390 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D390')
        d390 = rename_columns(D390, df_assets_f, version_f, 'D390')

        C850 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C850')
        c850 = rename_columns(C850, df_assets_f, version_f, 'C850')

        C890 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C890')
        c890 = rename_columns(C890, df_assets_f, version_f, 'C890')

        D590 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D590')
        d590 = rename_columns(D590, df_assets_f, version_f, 'D590')

        D410 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D410')
        d410 = rename_columns(D410, df_assets_f, version_f, 'D410')

        C790 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C790')
        c790 = rename_columns(C790, df_assets_f, version_f, 'C790')

        C590 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C590')
        c590 = rename_columns(C590, df_assets_f, version_f, 'C590')

        D300 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D300')
        d300 = rename_columns(D300, df_assets_f, version_f, 'D300')

        C690 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C690')
        c690 = rename_columns(C690, df_assets_f, version_f, 'C690')

        D690 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D690')
        d690 = rename_columns(D690, df_assets_f, version_f, 'D690')

        C390 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C390')
        c390 = rename_columns(C390, df_assets_f, version_f, 'C390')

        D696 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'D696')
        d696 = rename_columns(D696, df_assets_f, version_f, 'D696')

        C320 = Fiscal.filter(pl.col(dfn.REGISTRO) == 'C320')
        c320 = rename_columns(C320, df_assets_f, version_f, 'C320')

        Fiscal = pl.concat([c190, c320, c390, c490, c590, c690, c790, c850, c890, 
                            d190, d300, d390, d410, d590, d690, d696], how='diagonal')


        df_fisc_renomeado = Fiscal.with_columns(
            pl.coalesce([pl.col("VL_BC_ICMS2"), pl.col("VL_BC_ICMS")]).alias("VL_BC_ICMS"),
            pl.coalesce([pl.col("DT_DOC_INI"), pl.col("DT_DOC")]).alias("DT_DOC"),
            pl.coalesce([pl.col("CHV_CTE"), pl.col("CHV_NFE")]).alias("CHV_NFE"),
            pl.coalesce([pl.col("VL_ICMS2"), pl.col("VL_ICMS")]).alias("VL_ICMS"),
            pl.coalesce([pl.col("VL_BC_ICMS_ST2"), pl.col("VL_BC_ICMS_ST")]).alias("VL_BC_ICMS_ST"),
            pl.coalesce([pl.col("VL_ICMS_ST"), pl.col("VL_ICMS_ST2")]).alias("VL_ICMS_ST"),
            pl.coalesce([pl.col("VL_IPI2"), pl.col("VL_IPI")]).alias("VL_IPI"))
        
        return df_fisc_renomeado, df_cont_renomeado 