import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd


def empresa_cnpj(inbound, df):
    if (inbound.filter(pl.col(fd.IS_EFDC)).is_empty()) & (inbound.filter(pl.col(fd.IS_EFDF)).is_empty()):
        empresa = ""
        cnpj = ""
    else:
        empresaCNPJ = df.select(pl.col(cd.CNPJ), pl.col(cd.NOME))
        empresa = (empresaCNPJ.select([cd.NOME]).item(0,0))
        cnpj = (empresaCNPJ.select([cd.CNPJ]).item(0,0))
        
    return empresa, cnpj