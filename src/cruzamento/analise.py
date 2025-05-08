import polars as pl

def filtrar_fora_do_padrao(df, extensao, condicao, status):
    return df.filter(
        (pl.col("file_Name").str.ends_with(extensao)) & (~condicao)
    ).select([
        pl.col('file_Name').alias("NOME DO ARQUIVO"),
        pl.lit("Não Processado"). alias("PROCESSAMENTO"),
        pl.lit(status).alias("STATUS ARQUIVO")
    ])

def nfe_duplicada(df, id):
    duplicatas = pl.struct(id).is_duplicated()
    return(
        df.filter(duplicatas).unique(subset=[id], keep="first")
        .select([
            pl.col("file_Name").alias("NOME DO ARQUIVO"),
            pl.lit("Não Processado").alias("PROCESSAMENTO"),
            pl.lit("Nota fiscal eletrônica (NF-e) duplicada").alias("STATUS ARQUIVO")
        ])
    )

def count_arquivos(df_xml,  df_txt_contrib, df_txt_fiscal):

    count_qtd_xml = len(df_xml) 
    count_qtd_txt = len(df_txt_contrib) + len(df_txt_fiscal) 

    if count_qtd_xml == 0 and count_qtd_txt == 0:
        return pl.DataFrame({"STATUS ARQUIVO": ["Nenhum TXT SPED e XML NF-e encontrado"]})
    elif count_qtd_xml == 0:
        return pl.DataFrame({"STATUS ARQUIVO": ["Nenhum XML NF-e encontrado"]})
    elif count_qtd_txt == 0:
        return pl.DataFrame({"STATUS ARQUIVO": ["Nenhum TXT SPED encontrado"]})
    else:
        return None