import polars as pl
import datatricks.sped.sped_definitions as dfn
import datatricks.sped.content as ct
from datatricks.sped.cache import cache

def hierarquizacao(df, level, row):
    """Description:
        Get father-id of sped rows
    Parameters:
        df: dataframe
        level: int value that represent the level column index of a df.map_rows tuple
        row: int value that represent the index of a df.map_rows tuple
    Returns:
        Dataframe with hierarchy rows"""
    
    ch = cache()
    df = df.with_columns(df.map_rows(lambda x: (ch.get_parent_of(x[level], x[row]))))
    df = df.rename({'map':'ID-PAI'})
    return df

def text_consolidated(level, text, cache):
    """
    Description:
        Concatenate a sped row with all its parents
    Parameters:
        level: int value that represent the level column index of a df.map_rows tuple
        text: string that represent a sped row 
        cache: a cache dictionary from datatricks
    Returns:
        A string of a sped row and its parents 
    """
    cache[level] = text
    consolidado = ""
    if level == 0:
        consolidado = cache.get(0)
    else:    
        for i in range(1, level + 1):
            consolidado += cache.get(i)
    return consolidado

def consolidado(df, level, text):
    """Description:
        Consolidate all sped rows with its parents
    Parameters:
        df: dataframe
        level: int value that represent the level column index of a df.map_rows tuple
        text: string that represent a sped row 
    Returns:
        Dataframe 
    """

    cache = {}
    df = df.with_columns(
        df.map_rows(lambda x: (text_consolidated(x[level], x[text], cache)))
    )
    df = df.rename({'map':'texto_consolidado'})


    return df

def split(df, column, sep):
    """
    Description:
        Split a column into many, using a separator
    Parameters:
        df: dataframe
        column: column to be separated
        sep: separator to use it to split
    Returns:
        A dataframe with unnested columns. 
    """

    df = df.with_columns(pl.col(column).map_elements(lambda x: x.count(sep), return_dtype=pl.Int64).alias('field_count'))
    num_col_novas = df.select(pl.col('field_count').max()).item()
    df = df.with_columns(pl.col(column).str.split_exact(sep, num_col_novas)).unnest(column)

    return df

def find_date(date):
    date = f'{date[4:]}-{date[2:4]}-{date[0:2]}'
    return date

def get_sped_info(df, sped_type):
    """
    Description:
        get periodo, cnpj and version of sped file.
    Parameters:
        df: dataframe
        sped_type: sped type dictionary 
    Returns:
        dataframe with periodo, cnpj and version columns added
    """

    df = df.with_columns([
        pl.when(pl.col(dfn.REGISTRO).eq("0000"))
        .then(pl.col(sped_type[dfn.PERIODO])).otherwise(pl.lit(None)).alias(dfn.PERIODO),
        pl.when(pl.col(dfn.REGISTRO).eq('0000'))
        .then(pl.col(sped_type[dfn.CNPJ])).otherwise(pl.lit(None)).alias(dfn.CNPJ),
        pl.when(pl.col(dfn.REGISTRO).eq('0000'))
        .then(pl.col(sped_type[dfn.VERSAO])).otherwise(pl.lit(None)).alias(dfn.VERSAO)
    ])
    return df

def sped_treatment(df_sped):
    """
    Description:
        get rid of first |, \\n occurrences and get field registro
    Parameters:
        df_sped: df to be treated 
    Returns:
        a dataframe with new info. 
    """

    df_sped = df_sped.with_columns(pl.col(dfn.CONSOLIDADO).map_elements(lambda x: x[:-1], return_dtype=pl.Utf8).alias(dfn.CONSOLIDADO))
    df_sped = df_sped.with_columns(pl.col(dfn.CONSOLIDADO).map_elements(lambda x: x[1:], return_dtype=pl.Utf8).alias(dfn.CONSOLIDADO))
    df_sped = df_sped.with_columns(pl.col(dfn.CONSOLIDADO).map_elements(lambda x: x[0:4], return_dtype=pl.Utf8).alias(dfn.REGISTRO))
    df_sped = df_sped.with_row_index(name=dfn.ID_REG, offset=1)
    return df_sped

def assets_treatment(df_assets):
    """
    Description:
        Treat assets file to get rid of unused columns, and group by needed info
    Parameters:
        df_assets: df to be treated
    Returns:
        Dataframe needed info. 
    """

    df_assets = df_assets.select([dfn.REGISTRO, dfn.NIVEL])
    df_assets = df_assets.group_by(dfn.REGISTRO, maintain_order=True).first()
    return df_assets

def merge_dfs(df_sped, df_assets):
    """
    Description:
        Merge two dfs
    Parameters:
        df_sped: first df
        df_assets: second df
    Returns:
        a merged df
    """

    df_sped = df_sped.lazy()
    df_assets = df_assets.lazy()
    joined_df = df_sped.join(df_assets, how='inner', on=dfn.REGISTRO)
    df_merged = joined_df.collect(streaming=True)
    return df_merged

def dataframe_treatment(df_sped, df_assets, sped_type):
    """
    Description:
        Function that concat three functions of treatment inside it. 
        There's filter, treatment and merge. all cited above
    Parameters:
        df_sped: sped df
        df_assets: assets df
        sped_type: sped_type dictionary 
    Returns:
        Dataframe with all treatments
    """
    if sped_type[dfn.OBRIGACAO] == dfn.ECD[dfn.OBRIGACAO]:
        df_sped = df_sped.filter(pl.col(dfn.CONSOLIDADO).str.starts_with('|'))
        df_sped = sped_treatment(df_sped)
        df_assets = assets_treatment(df_assets)
        df = merge_dfs(df_sped, df_assets)
        df = treat_exceptions(df)
    else:
        df_sped = sped_treatment(df_sped)
        df_assets = assets_treatment(df_assets)
        df = merge_dfs(df_sped, df_assets)

        
    return df.sort(by=[dfn.ID_REG])

def apply_versao(idsped, dicionario):
    return dicionario[idsped]
    
def fill_sped_nulls(df, sped_type, dicionario = {}):
    """Description:
        Fill null values
    Parameters:
        df: sped df
        sped_type: sped_type dictionary
        dicionario: version dict on ECDs, generated at get_version function. Else a placeholder.
    Returns:
        a merged df"""
    df = df.with_columns(pl.col(dfn.ID_PAI).fill_null(0))
    df = df.with_columns(pl.col(dfn.PERIODO).forward_fill())
    df = df.with_columns(pl.col(dfn.CNPJ).forward_fill())
    df = df.with_columns(pl.col(dfn.PERIODO).map_elements(lambda x: find_date(x), return_dtype=pl.Utf8))
    df = df.with_columns(pl.col(dfn.PERIODO).str.strptime(pl.Date, format='%Y-%m-%d'))
    
    if sped_type[dfn.OBRIGACAO] == dfn.ECD[dfn.OBRIGACAO]:
        df = df.with_columns(pl.col(dfn.ID_SPED).map_elements(lambda x: apply_versao(x, dicionario), return_dtype=pl.Utf8).alias(dfn.VERSAO))
    else:
        df = df.with_columns(pl.col(dfn.VERSAO).forward_fill())
    return df

def order_sped_columns( df):
    """Description:
        Order df and get rid of unused columns
    Parameters:
        df: sped df
    Returns:
        A merged"""
    columns = [dfn.PERIODO, dfn.REGISTRO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI, dfn.ID_REG, dfn.VERSAO]
    temp = [f'field_{i}' for i in range(0, df.select(pl.col('field_count').max()).item() + 1)]

    columns.extend(temp)
    df = df.select(columns)
    return df

def get_version(df):
    """Description:
        Get version of sped file
    Parameters:
        df: sped df
    Returns:
        A dict with the {id_file: version} structure"""
    temp_df = df.filter(pl.col(dfn.REGISTRO) == 'I010')
    temp_df = temp_df.with_columns(pl.col('field_4').map_elements(lambda x: '000' + x[0], return_dtype=pl.String).alias(dfn.VERSAO))
    temp_df = temp_df.select([dfn.ID_SPED, dfn.VERSAO])
    dictionary = temp_df.rows()
    dicionario = {}
    for items in dictionary:
        dicionario[items[0]] = items[1]
    return dicionario

def df_treatment_pre_file_generation(df, sped_type):
    """Description:
        Function that concat three other functions, to get sped info, fill nulls and order columns
        All cited above.
    Parameters:
        df: sped df
    Returns:
        df treated, ready to be written."""
    df = get_sped_info(df, sped_type)
    if sped_type[dfn.OBRIGACAO] == dfn.ECD[dfn.OBRIGACAO]:
        dicionario = get_version(df)
        df = fill_sped_nulls(df, sped_type, dicionario)
    else:
        df = fill_sped_nulls(df, sped_type)
    df = order_sped_columns(df)
    return df 

def remove_equals(df):
    df = df.with_columns([
        pl.col(col).str.replace(r"^=", "'=") if df[col].dtype == pl.Utf8 else pl.col(col)
        for col in df.columns
    ])
    return df


def df_treatment_pre_file_generation(df, sped_type):
    """Description:
        Function that concat three other functions, to get sped info, fill nulls and order columns
        All cited above.
    Parameters:
        df: sped df
    Returns:
        df treated, ready to be written."""
    df = get_sped_info(df, sped_type)
    df = fill_sped_nulls(df, sped_type)

    df = order_sped_columns(df)
    return df 

def add_pipes(consolidado, lista_i):
    register = consolidado[0:4]

    match register:
        case 'I200':
            if consolidado.count('|') == 5:
                num_of_pipes = lista_i[f'{register} - 1'] - (consolidado.count('|'))
            else:     
                num_of_pipes = lista_i[f'{register} - 2'] - (consolidado.count('|'))
        case _:
            try:
                num_of_pipes = lista_i[register] - (consolidado.count('|'))
            except:
                num_of_pipes = 0

    pipes = '|' * num_of_pipes

    return consolidado + pipes
    
def treat_exceptions(df, lista_i=dfn.ECD[dfn.DICT_CAMPO_QTD]):
    """
    Description:
        Function that treats ECD bussiness rule of optional files on certain registers.
    Parameters:
        df: sped df
        lista_i: dict of optional fields on ECD
    Returns:
        A df with new pipes on the rows.
    """

    df = df.with_columns(pl.col(dfn.CONSOLIDADO).map_elements(lambda x: add_pipes(x, lista_i), return_dtype=pl.Utf8).alias(dfn.CONSOLIDADO))
    df = df.drop('field_count')

    return df

def read_assets(assets_path, sped_type):
    """
    Description:
        Read asset file
    Parameters:
        assets_path: path of asset file
        sped_type: sped_type dictionary
    Returns:
        Report Dataframe
    """
    dtypes = {
        dfn.REGISTRO: pl.Utf8,
        dfn.VERSAO: pl.Utf8,
        dfn.NIVEL: pl.UInt32,
        dfn.CAMPO: pl.Utf8}
    return pl.read_excel(assets_path[sped_type[dfn.ASSET]], schema_overrides=dtypes)


def quebra(inbound, df_asset, sped_type):
    df_sped = ct.read_sped_files(inbound)
    df_sped = df_sped.rename({'id_file':dfn.ID_SPED})
    df = dataframe_treatment(df_sped, df_asset, sped_type)
    df = hierarquizacao(df, 5, 0)
    df = consolidado(df, 5, 1)
    df = split(df, 'texto_consolidado', "|")
    df = remove_equals(df)
    df = df_treatment_pre_file_generation(df, sped_type)
    return df