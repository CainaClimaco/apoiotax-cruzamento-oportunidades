import os, sys
import polars as pl
import cruzamento.cruzamento_definition as cd
def filtrar_fora_do_padrao(df, extensao, obrigacao, status):
    """
    Description:
        Filtra arquivos que não atendem à obrigação especificada, com base na extensão.
    Parameters:
        df: Dataframe com as informações dos arquivos.
        extensão: Extensão dos arquivos que devem ser filtrados (ex: '.xml', '.txt').
        obrigação: Indica a obrigação (ex: EFD, NF-e).
        status: Mensagem usada na coluna de status.
    Returns:
        Dataframe contendo os arquivos que não atendem à obrigação, com as seguintes colunas:
            file_Name: Nome do arquivo.
            Processamento: Indica se o arquivo foi processado.
            Status: Informa o motivo do não processamento do arquivo. 
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
        Identifica os registros duplicados com base no campo identificador.
    Parameters:
        df: Dataframe com as informações das Notas Fiscais.
        id: Coluna contendo o identificador único da nota.
    Returns:
        Dataframe contendo as notas duplicadas, com as seguintes colunas:
            file_Name: Nome do arquivo.
            Processamento: Indica se o arquivo foi processado.
            Status: Informa o motivo do não processamento do arquivo. 
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
        Conta a quantidade de arquivos XML e TXT não nulos e valida se existe dado a ser processado.
    Parameters:
        df_xml: Dataframe contendo os arquivos XML (NF-e)
        df_txt_contrib: Dataframe contendo as informações da EFD Contribuições
        df_txt_fiscal: Dataframe contendo as informações da EFD ICMS-IPI
    Returns:
        pl.Dataframe: Dataframe com o status informando caso haja a ausência de arquivos de cada obrigação. 
        Encerra a execução se todos estiverem vazios.
    """
    df_xml = df_xml.filter(~pl.all_horizontal(pl.all().is_null()))
    df_txt_contrib = df_txt_contrib.filter(~pl.all_horizontal(pl.all().is_null()))
    df_txt_fiscal = df_txt_fiscal.filter(~pl.all_horizontal(pl.all().is_null()))

    count_qtd_xml = len(df_xml) 
    count_qtd_txt = len(df_txt_contrib) + len(df_txt_fiscal) 

    if count_qtd_xml == 0 and count_qtd_txt == 0:
        self.logger.error("Nenhum TXT SPED e XML NF-e encontrado. Encerrando execução.")
        sys.exit()
    elif count_qtd_xml == 0:
        return pl.DataFrame({cd.status: ["Nenhum XML NF-e encontrado"]})
    elif count_qtd_txt == 0:
        return pl.DataFrame({cd.status: ["Nenhum TXT SPED encontrado"]})
    else:
        return pl.DataFrame({cd.status: [None]})