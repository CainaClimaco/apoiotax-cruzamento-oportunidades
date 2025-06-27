import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd


def empresa_cnpj(inbound, df_fiscal, df_contribuicoes):
    """
    Description:
        Extracts the company name and CNPJ information.
    Parameters:
        inbound: Dataframe containing information about the recieved files.
        df_fiscal: Dataframe containing the file information.
        df_contribuicoes: Dataframe containing the file information.

    Returns:
        empresa: extracted name of the company.
        cnpj: extracted CNPJ number.
    """
    
    if (inbound.filter(pl.col(fd.IS_EFDC)).is_empty()) & (inbound.filter(pl.col(fd.IS_EFDF)).is_empty()):
        empresa = ""
        cnpj = ""
    else:
        df_empresa = pl.concat([
        df_contribuicoes.select([cd.NOME, cd.CNPJ, cd.Registro]).filter(pl.col(cd.Registro) == '0000'),
        df_fiscal.select([cd.NOME, cd.CNPJ, cd.Registro]).filter(pl.col(cd.Registro) == '0000')
    ])
        empresaCNPJ = df_empresa.unique(subset=[cd.CNPJ], keep="first")
        empresa = (empresaCNPJ.select([cd.NOME]).item(0,0))
        cnpj = (empresaCNPJ.select([cd.CNPJ]).item(0,0))
        
    return empresa, cnpj