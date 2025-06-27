import polars as pl
import cruzamento.cruzamento_definition as cd

def filtro_contribuicoes(df):
    filtro_1 = df.filter((pl.col(cd.Registro) == "A170") & (pl.col(cd.IND_OPER) == "1"))
    resto_1 = df.filter(pl.col(cd.Registro) != "A170")  
    
    filtro_2 = resto_1.filter((pl.col(cd.Registro) == "C170") & (pl.col(cd.IND_OPER) == "1"))

    c170_mod_dif_55 = filtro_2.filter(pl.col(cd.COD_MOD) != "55")
    

    mod_55 = filtro_2.filter(pl.col(cd.COD_MOD) == "55")
   
    mod_55_escri_2 = mod_55.filter(pl.col(cd.IND_ESCRI) == "2")
    
    cst_validos = mod_55_escri_2.filter(pl.col(cd.CST).is_in(["01", "02", "03", "04", "05"]))
    aliquota_diferente_zero = cst_validos.filter(pl.col(cd.ALIQ) != "0")


    cst_invalidos = mod_55_escri_2.filter(~pl.col(cd.CST).is_in(["01", "02", "03", "04", "05"]))  
    aliquota_nao_nula = cst_invalidos.filter(pl.col(cd.ALIQ) != "")

    filtro_2 = pl.concat([aliquota_nao_nula, aliquota_diferente_zero, c170_mod_dif_55])
    
    resto_2 = resto_1.filter(pl.col(cd.Registro) != "C170")
    
    filtro_3 = resto_2.filter(
    (pl.col(cd.Registro).is_in(["C185", "C495", "C181", "C491"])) & (pl.col(cd.IND_ESCRI) == "1")
    )
    
    resto_3 = resto_2.filter(~((pl.col(cd.Registro).is_in(["C185", "C495", "C181", "C491"]))))
    
    filtro_4 = resto_3.filter(
    (pl.col(cd.Registro).is_in(["C485", "C481"])) & (pl.col(cd.IND_ESCRI) == "2")
    )
   
    resto_4 = resto_3.filter(~((pl.col(cd.Registro).is_in(["C485", "C481"]))))
    
    filtro_5 = resto_4.filter((pl.col(cd.Registro) == "F100") & (pl.col(cd.IND_OPER).is_in(["1", "2"])))
    
    filtro_6 = resto_4.filter(~((pl.col(cd.Registro) == "F100")))
    
    resultado_final = pl.concat([filtro_1, filtro_2, filtro_3, filtro_4, filtro_5, filtro_6])

    return resultado_final