import os, sys
import polars as pl
import cruzamento.cruzamento_definition as cd
def filtrar_fora_do_padrao(df, extensao, condicao, status):
    return df.filter(
        (pl.col("file_Name").str.ends_with(extensao)) & (~condicao)
    ).select([
        pl.col('file_Name').alias(cd.file_name),
        pl.lit("Não Processado"). alias(cd.processamento),
        pl.lit(status).alias(cd.status)
    ])

def nfe_duplicada(df, id):
    duplicatas = pl.struct(id).is_duplicated()
    return(
        df.filter(duplicatas).unique(subset=[id], keep="first")
        .select([
            pl.col("file_Name").alias(cd.file_name),
            pl.lit("Não Processado").alias(cd.processamento),
            pl.lit("Nota fiscal eletrônica (NF-e) duplicada").alias(cd.status)
        ])
    )


def count_arquivos(df_xml, df_txt_contrib, df_txt_fiscal,self):
    df_xml = df_xml.filter(~pl.all_horizontal(pl.all().is_null()))
    df_txt_contrib = df_txt_contrib.filter(~pl.all_horizontal(pl.all().is_null()))
    df_txt_fiscal = df_txt_fiscal.filter(~pl.all_horizontal(pl.all().is_null()))

    count_qtd_xml = len(df_xml) 
    count_qtd_txt = len(df_txt_contrib) + len(df_txt_fiscal) 
    print(count_qtd_txt)
    print(count_qtd_xml)

    if count_qtd_xml == 0 and count_qtd_txt == 0:
        self.logger.error("Nenhum TXT SPED e XML NF-e encontrado. Encerrando execução.")
        sys.exit()
    elif count_qtd_xml == 0:
        return pl.DataFrame({cd.status: ["Nenhum XML NF-e encontrado"]})
    elif count_qtd_txt == 0:
        return pl.DataFrame({cd.status: ["Nenhum TXT SPED encontrado"]})
    else:
        return pl.DataFrame({cd.status: [None]})