import polars as pl
import cruzamento.transpose as tr
import cruzamento.cruzamento_definition as cd
import datatricks.sped.conversor_sped as cv
import datatricks.sped.conversor_xml as cx


def renomear_colunas(df, mapping: dict[str, str]):
    exprs = []
    for novo_nome, nomes_antigos in mapping.items():
        nomes = [nomes_antigos] if isinstance(nomes_antigos, str) else nomes_antigos
        colunas_existentes = [pl.col(n) for n in nomes if n in df.columns]
        if colunas_existentes:
            exprs.append(pl.coalesce(colunas_existentes).alias(novo_nome))
    return df.select(exprs + [pl.col(c) for c in df.columns if c not in sum([v if isinstance(v, list) else [v] for v in mapping.values()], [])])


def leitor_sped(inbound, obrigacao, sped_type, definition, registros, path_env):
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
            df_padrao = tr.sped_padrao(sped_type, registros, path_env)
            df_padrao = renomear_colunas(df_padrao, cd.PADRAO)
            
    else:
            df_efd = inbound.filter(pl.col(obrigacao) == True)
            df_padrao = cv.quebra(df_efd, sped_type, path_env)

            df_padrao = df_padrao.with_columns([
                pl.when(pl.col(cd.Registro).eq("0000"))
                .then(pl.col(definition["0000"][cd.NOME])).otherwise(pl.lit(None)).alias(cd.NOME),
                pl.when(pl.col(cd.Registro).eq("C100"))
                .then(pl.col(definition["C100"][cd.COD_SIT])).otherwise(pl.lit(None)).alias(cd.COD_SIT),
                pl.when(pl.col(cd.Registro).eq("C100")) 
                .then(pl.col(definition["C100"][cd.CHV_NFE])).otherwise(pl.lit(None)).alias(cd.CHV_NFE),
                pl.when(pl.col("Registro").eq("0150"))
                .then(pl.col(definition["0150"][cd.NOME_DEST])).otherwise(pl.lit(None)).alias(cd.NOME_DEST),
                pl.when(pl.col("Registro").eq("0150")) 
                .then(pl.col(definition["0150"][cd.CNPJ_DEST])).otherwise(pl.lit(None)).alias(cd.CNPJ_DEST),
                pl.when(pl.col("Registro") == "C100")
                .then(pl.col(definition["C100"][cd.COD_PART])).otherwise(None).alias("COD_PART_C100"),
                pl.when(pl.col("Registro") == "0150")
                .then(pl.col(definition["0150"][cd.COD_PART])).otherwise(None).alias("COD_PART_0150")
            ])
            df_padrao = df_padrao.with_columns([
                pl.coalesce([pl.col("COD_PART_C100"), pl.col("COD_PART_0150")]).alias(cd.COD_PART)
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

        dados = {col: [None] for col in field_list}
        NFe = pl.DataFrame(dados)
        NFe = NFe.with_columns(
             pl.lit(None).alias("file_Name")
        )
        NFe = NFe.cast(pl.String)
        NFe = (renomear_colunas(NFe, rename))
        
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
 
        