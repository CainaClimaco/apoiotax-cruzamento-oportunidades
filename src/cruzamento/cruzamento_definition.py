NOME = 'NOME'
CNPJ = 'CNPJ'
COD_SIT = 'COD_SIT'
CHV_NFE = 'CHV_NFE'
VERSAO = 'VERSAO' 
PERÍODO = 'Período'
ID = 'ID'
CNPJ_EMIT = 'CNPJ_EMIT'
CNPJ_DEST = 'CNPJ_DEST'
SITUACAO = 'SITUAÇÃO NFE'
CFOP = 'CFOP'
COD_SIT_EFDC = "Código"
DESC_COD_SIT_EFDC = "Descrição"
COD_SIT_EFDF = "COD_SIT_EFDF"
DESC_COD_SIT_EFDF = "DESC_COD_SIT_EFDF"
Registro = 'Registro'
file_name = "NOME DO ARQUIVO"
processamento = "PROCESSAMENTO"
status = "STATUS ARQUIVO"


VERSAO_EFDC = '006' 
VERSAO_EFDF = '018'
CAMINHO_EFDC = 'src\\assets\\Registros EFD Contribuicoes v7.xlsx'
CAMINHO_EFDF = 'src\\assets\\Registros EFD ICMS IPI.xlsx'
CAMINHO_SITUACAO = 'src\\assets\\Situacao_NF-e.xlsx'
status_txt = "Arquivo TXT fora do padrão EFD ICMS/IPI"
status_xml = "Arquivo XML fora do padrão nota fiscal eletrônica (NF-e) - Modelo 55"
status_nfe = "Nota fiscal eletrônica (NF-e) duplicada"


EFDC = {NOME: 'field_7',
        CNPJ: 'Quebra CNPJ',
        COD_SIT: 'field_10',
        CHV_NFE: 'field_13'
}

EFDF = {NOME: 'field_5',
        CNPJ: 'Quebra CNPJ',
        COD_SIT: 'field_7',
        CHV_NFE: 'field_10'
}

PADRAO_EFDC = { Registro: 'REG',
                COD_SIT: 'COD_SIT;'
}
PADRAO_EFDF = {
        Registro: 'REG'
}

NFE = { PERÍODO: 'nfeProc_NFe_infNFe_ide_dhEmi',
        ID: 'nfeProc_NFe_infNFe_Id',
        CNPJ_EMIT: 'nfeProc_NFe_infNFe_emit_CNPJ',
        CNPJ_DEST: 'nfeProc_NFe_infNFe_dest_CNPJ',
        SITUACAO:'nfeProc_protNFe_infProt_xMotivo',
        CFOP: 'nfeProc_NFe_infNFe_det_prod_CFOP',
        CHV_NFE:'nfeProc_protNFe_infProt_chNFe'
}
