"""Diagnóstico: quais colunas reais existem no registro 0000 após o parsing."""
import sys, os
sys.path.insert(0, 'src')

import datatricks.sped.conversor_sped as cv
import datatricks.sped.sped_definitions as dfn

# Variáveis de ambiente mínimas
path_env = {}

print("=== dfn constants ===")
print("dfn.PERIODO =", repr(dfn.PERIODO))
print("dfn.VERSAO  =", repr(dfn.VERSAO))
efdc_periodo = dfn.EFDC.get(dfn.PERIODO)
efdf_periodo = dfn.EFDF.get(dfn.PERIODO)
efdc_versao  = dfn.EFDC.get(dfn.VERSAO)
efdf_versao  = dfn.EFDF.get(dfn.VERSAO)
print(f"EFDC => PERIODO field: {efdc_periodo!r}  VERSAO field: {efdc_versao!r}")
print(f"EFDF => PERIODO field: {efdf_periodo!r}  VERSAO field: {efdf_versao!r}")

# Calculate end-date field (next field_N)
for label, ini_f in [("EFDC", efdc_periodo), ("EFDF", efdf_periodo)]:
    if ini_f and ini_f.startswith("field_"):
        fin_f = "field_" + str(int(ini_f.replace("field_", "")) + 1)
        print(f"  {label} DT_FIN would be at: {fin_f!r}")
