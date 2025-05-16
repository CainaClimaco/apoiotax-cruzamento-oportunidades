import polars as pl
import cruzamento.transpose as tr
import cruzamento.cruzamento_definition as cd
import datatricks.sped.conversor_sped as cv
import datatricks.sped.conversor_xml as cx

def renomear_colunas(df, mapping: dict[str, str]):
    """
    Description:
        Renomeia as colunas do Datafrae com base em um aquivos de definições.
    Parameters:
        df: Dataframe original no qual as colunas serão renomeadas.
        mapping: Mapeamento do nome das colunas.
    Returns:
        Dataframe com as colunas renomeadas. 
    """
    rename_dict = {v: k for k,v in mapping.items()}
    return df.rename(rename_dict)

def leitor_sped(inbound, obrigacao, sped_type, versao, padrao, definition):
    """
    Description:
        Lê e processa arquivos SPED
    Parameters:
        inbound: Dataframe com as informações sobre os arquivos recebidos.
        obrigacao: Indica a obrigação (ex: EFDC, EFDF).
        sped_type: Dicionário do tipo SPED.
        versao: Versão do layout EFD.
        padrao: Dicionário com as colunas padrão
        definition: Dicionário com os nomes padronizados das colunas.
    Returns:
        Dataframe processado e padronizado. 
    """
    if inbound.filter(pl.col(obrigacao)).is_empty():
            df_padrao = tr.sped_padrao(sped_type, versao)
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


def leitor_nfe(inbound, obrigacao, definition, status):
    """
    Description:
        Lê e processa os arquivos XML de NF-e.
    Parameters:
        inbound: Dataframe com as informações sobre os arquivos recebidos.
        obrigacao: Indica a obrigação (ex: NF-e).
        definition: Dicionário com os nomes padronizados das colunas.
    Returns:
        Dataframe com os dados extraídos dos arquivos XML de NF-e. 
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
        NFe = cx.conversor_xml(df_xml, field_list=[ 'nfeProc_NFe_infNFe_ide_dhEmi', 
                                                    'nfeProc_NFe_infNFe_Id', 
                                                    'nfeProc_NFe_infNFe_emit_CNPJ', 
                                                    'nfeProc_NFe_infNFe_dest_CNPJ', 
                                                    'nfeProc_protNFe_infProt_xMotivo', 
                                                    'nfeProc_NFe_infNFe_ide_tpNF', 
                                                    'nfeProc_protNFe_infProt_chNFe'])
        validos = NFe.filter(pl.col("Xml_Content").is_not_null())
        invalidos = NFe.filter(pl.col('Xml_Content').is_null())

        if not validos.is_empty():
            validos = (renomear_colunas(validos, definition))
            validos = validos.with_columns(
                pl.col(cd.PERÍODO).str.slice(0,10).str.strptime(pl.Date, strict=False),
                pl.col(cd.tpNF).cast(pl.Int32))
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
 
        