import polars as pl
import cruzamento.transpose as tr
import cruzamento.cruzamento_definition as cd
import datatricks.sped.conversor_sped as cv
import datatricks.sped.conversor_xml as cx


def renomear_colunas(df, mapping: dict[str, str]):
    """
    Description:
        Renames the Dataframe columns based on a definition file.
    Parameters:
        df: Original Dataframe in which the columns will be renamed.
        mapping: Dictionary mapping the column names.
    Returns:
        Dataframe with the columns renamed. 
    """
    rename_dict = {v: k for k,v in mapping.items()}
    return df.rename(rename_dict)


def leitor_sped(inbound, obrigacao, sped_type, padrao, definition):
    """
    Description:
        Reads and processes SPED files
    Parameters:
        inbound: Dataframe containing information about the recieved files.
        obrigacao: Indicates the tax obligation (e.g., EFDC, EFDF).
        sped_type: sped type dictionary.
        padrao: Dictionary containing the normalized column names.
        definition: Dictionary used to rename the Dataframe columns.
    Returns:
        Dataframe with the data extracted from the sped files.
    """
    if inbound.filter(pl.col(obrigacao)).is_empty():
            df_padrao = tr.sped_padrao(sped_type)
            df_padrao = renomear_colunas(df_padrao, padrao)
    else:
            df_efd = inbound.filter(pl.col(obrigacao) == True)
            df_padrao = cv.quebra(df_efd, sped_type)
            df_padrao = df_padrao.with_columns([
                pl.when(pl.col("Registro").eq("0000"))
                .then(pl.col(definition[cd.NOME])).otherwise(pl.lit(None)).alias(cd.NOME),
                pl.when(pl.col("Registro").eq("0000"))
                .then(pl.col(definition[cd.CNPJ])).otherwise(pl.lit(None)).alias(cd.CNPJ),
                pl.when(pl.col("Registro").eq("C100"))
                .then(pl.col(definition[cd.COD_SIT])).otherwise(pl.lit(None)).alias(cd.COD_SIT),
                pl.when(pl.col("Registro").eq("C100")) 
                .then(pl.col(definition[cd.CHV_NFE])).otherwise(pl.lit(None)).alias(cd.CHV_NFE)
            ])
    return df_padrao


def leitor_nfe(inbound, obrigacao, status, regex_list=[], rename=[], field_list=[]):
    """
    Description:
        Reads and processes XML files (NF-e).
    Parameters:
        inbound: Dataframe containing information about the recieved files.
        obrigacao:  Indicates the tax obligation (ex: NF-e).
        status: Message used in the status column. 
    Returns:
        Dataframe with the data extracted from the NF-e XML files. 
    """
    if inbound.filter(pl.col(obrigacao)).is_empty():
        NFe = pl.DataFrame({
            'file_Name': None,
            'Período': None ,
            'ID': None,
            'CNPJ_EMIT':None,
            'CNPJ_DEST': None,
            'SITUAÇÃO NFE': None,
            'tpNF': None,
            'CHV_NFE':None
            })
        xml_erro = pl.DataFrame({
            'NOME DO ARQUIVO': None,
            'PROCESSAMENTO': None ,
            'STATUS ARQUIVO': None})
        return NFe,xml_erro
    else:
        df_xml = inbound.filter(pl.col(obrigacao) == True)
        NFe = cx.conversor_xml(df_xml, regex_list, field_list)
        validos = NFe.filter(pl.col("Xml_Content").is_not_null())
        invalidos = NFe.filter(pl.col('Xml_Content').is_null())

        if not validos.is_empty():
            validos = (renomear_colunas(validos, rename))
        if not invalidos.is_empty():
            xml_erro = invalidos.select([
                pl.col('file_Name').alias(cd.file_name),
                pl.lit("Não Processado"). alias(cd.processamento),
                pl.lit(status).alias(cd.status)
            ])
        else:
            xml_erro = pl.DataFrame({
            'NOME DO ARQUIVO': None,
            'PROCESSAMENTO': None ,
            'STATUS ARQUIVO': None})
             
        return validos, xml_erro
 
        