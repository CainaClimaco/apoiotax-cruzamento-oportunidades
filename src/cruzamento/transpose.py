import polars as pl
import datatricks.sped.conversor_sped as cs
import cruzamento.cruzamento_definition as cd

def sped_padrao(sped_type):
    """
    Description:
        Reads an Excel file with the SPED layout and transpose it into a Dataframe
    Parameters:
        sped_type: Sped type dictionary
    Returns:
        A transposed Dataframe with the base structure of the SPED. 
    """
    df_padrao = (cs.get_remote_assets(sped_type))
    versao = df_padrao.select(pl.col(cd.VERSAO).max()).item(0, 0)

    df_padrao = df_padrao.filter(((pl.col("Registro") == 'C100') & (pl.col(cd.VERSAO) == versao)) | 
        ((pl.col("Registro") == '0000') & (pl.col(cd.VERSAO) == versao))) 


    contadores = {}
    novo_campo = []

    for valor in df_padrao['Campo']:
        valor_str = str(valor)
        contadores[valor_str] = contadores.get(valor_str, 0) + 1
        if contadores[valor_str] == 1:
            novo_campo.append(valor_str)
        else:
            novo_campo.append(f"{valor_str}_{contadores[valor_str]-1}")


    df_padrao = df_padrao.with_columns([
        pl.Series("Campo", novo_campo)
    ])
    df_transpose = df_padrao.transpose(column_names="Campo")
    df_transpose = (df_transpose.with_columns([
        pl.col(col).map_elements(lambda x: None if isinstance(x, str) else x, return_dtype=df_transpose.schema[col])
        for col in df_transpose.columns])
        .with_columns([pl.lit(None).alias("Período")])
        .unique(subset=["REG"], keep="first"))
            
    df_transpose = df_transpose.with_columns(pl.col("Período").cast(pl.Date))      
     
    return df_transpose

