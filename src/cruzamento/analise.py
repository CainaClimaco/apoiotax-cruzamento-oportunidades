import sys
import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd


def filtrar_fora_do_padrao(df, extensao, obrigacao, status):
    """
    Description:
        Filter the files that do not meet the specified tax obligation, based on the extension.
    Parameters:
        df: Dataframe containing the file information.
        extensão: File extension to be filterd (e.g., '.xml', '.txt').
        obrigação: Indicates the type of tax obligation (e.g., EFD, NF-e).
        status: Message used in the status column.
    Returns:
        Dataframe containing the files that do not meet the requirement, with the following columns:
            file_Name: File name.
            Processamento: Indicates whether the file was processed.
            Status: Provides the reason why the file was not processed. 
    """
    return df.filter(
        (pl.col("file_Name").str.ends_with(extensao)) & (~obrigacao)
    ).select([
        pl.col('file_Name').alias(cd.file_name),
        pl.lit("Não Processado"). alias(cd.processamento),
        pl.lit(status).alias(cd.status)
    ])


def nfe_duplicada(df, id):
    """
    Description:
        Identifies duplicated records based on the identifier field.
    Parameters:
        df: Dataframe containing the NF-e information.
        id: Column containing the NF-e unique identifier.
    Returns:
        Dataframe containing the files that do not meet the requirement, with the following columns:
            file_Name: File name.
            Processamento: Indicates whether the file was processed.
            Status: Provides the reason why the file was not processed.
    """
    duplicatas = pl.col(id).is_duplicated()
    return(
        df.filter(duplicatas).unique(subset=[id], keep="first")
        .select([
            pl.col("file_Name").alias(cd.file_name),
            pl.lit("Não Processado").alias(cd.processamento),
            pl.lit("Nota fiscal eletrônica (NF-e) duplicada").alias(cd.status)
        ])
    )


def count_arquivos(df_xml, df_txt_contrib, df_txt_fiscal,self):
    """
    Description:
        Counts the number of non-null XML and TXT files and checks whether there is data to be processed.
    Parameters:
        df_xml: Dataframe containing the XML files (NF-e).
        df_txt_contrib: Dataframe containing the EFD Contribuições information.
        df_txt_fiscal: Dataframe containing the EFD ICMS-IPI information.
    Returns:
        pl.Dataframe: Dataframe with a status indicating if any obligation files are missing.. 
        It terminates the execution if all dataframes ar empty.
    """
    df_xml = df_xml.filter(~pl.all_horizontal(pl.all().is_null()))
    df_txt_contrib = df_txt_contrib.filter(~pl.all_horizontal(pl.all().is_null()))
    df_txt_fiscal = df_txt_fiscal.filter(~pl.all_horizontal(pl.all().is_null()))

    count_qtd_xml = len(df_xml) 
    count_qtd_txt = len(df_txt_contrib) + len(df_txt_fiscal) 

    if count_qtd_xml == 0 and count_qtd_txt == 0:
        self.logger.error("ERRO: Nenhum TXT SPED e XML NF-e encontrado. Encerrando execução.")
        sys.exit()
    elif count_qtd_xml == 0:
        return pl.DataFrame({cd.status: ["Nenhum XML NF-e encontrado"]})
    elif count_qtd_txt == 0:
        return pl.DataFrame({cd.status: ["Nenhum TXT SPED encontrado"]})
    else:
        return pl.DataFrame({cd.status: [None]})
    
    
def analise(NFe, xml_erro, df_contribuicoes, df_fiscal, self, inbound):
    
    erro = count_arquivos(NFe, df_contribuicoes, df_fiscal, self)        
    xml = filtrar_fora_do_padrao(inbound, '.xml', pl.col(fd.IS_NFE), cd.status_xml)
    txt = filtrar_fora_do_padrao(inbound, '.txt', pl.col(fd.IS_EFDC) | pl.col(fd.IS_EFDF), cd.status_txt)
    duplicada = nfe_duplicada(NFe, cd.CHV_NFE)

    analise = pl.concat([xml, txt, duplicada, erro, xml_erro], how="diagonal")
    analise = analise.sort("STATUS ARQUIVO", 'NOME DO ARQUIVO').filter(~pl.all_horizontal(pl.all().is_null()))
    
    return analise


def nConsiderado (NFe):

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
                                            pl.col(cd.vICMSDeson), pl.col(cd.CALC_CONFRONTO), pl.col(cd.ANO))