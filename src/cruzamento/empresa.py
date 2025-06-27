import polars as pl
import cruzamento.cruzamento_definition as cd
import datatricks.io.file_definitions as fd


def empresa_cnpj(inbound, df):
    df.filter(~pl.all_horizontal(pl.all().is_null()))
    if df.height > 0:
        empresaCNPJ = df.select(pl.col(cd.CNPJ), pl.col(cd.NOME))
        empresa = (empresaCNPJ.select([cd.NOME]).item(0,0))
        cnpj = (empresaCNPJ.select([cd.CNPJ]).item(0,0))
    else:
        empresa = ""
        cnpj = ""

    return empresa, cnpj