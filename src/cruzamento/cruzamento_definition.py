NOME = 'NOME'
CNPJ = 'CNPJ'
COD_SIT = 'COD_SIT'
COD_PART = 'COD_PART'
CHV_NFE = 'CHV_NFE'
VERSAO = 'Versao' 
PERÍODO = 'Período'
ID = 'ID'
CNPJ_EMIT = 'CNPJ_EMIT'
CNPJ_DEST = 'CNPJ_DEST'
Registro = 'Registro'
file_name = "NOME DO ARQUIVO"
processamento = "PROCESSAMENTO"
status = "STATUS ARQUIVO"


CAMPOS_ESCRITURACAO = "CAMPOS_E"
COD_SIT_EFDC = "Código"
DESC_COD_SIT_EFDC = "Descrição"
COD_SIT_EFDF = "COD_SIT_EFDF"
DESC_COD_SIT_EFDF = "DESC_COD_SIT_EFDF"
SITUACAO = 'SITUAÇÃO NFE'
tpNF = 'tpNF'
rename_e = "rename_e"


CAMPOS_RECEITA = "CAMPOS_R"
rename_r = "rename_r"
VL_REC_COMP = "VL_REC_COMP"
NUM_DOC = "NUM_DOC"
DT_DOC = "DT_DOC"
CFOP = "CFOP"
CST_ICMS = "CST_ICMS"
ALIQ_ICMS = "ALIQ_ICMS"
VL_OPR = "VL_OPR"
VL_BC_ICMS = "VL_BC_ICMS"
VL_ICMS = "VL_ICMS"
VL_BC_ICMS_ST = "VL_BC_ICMS_ST"
VL_ICMS_ST = "VL_ICMS_ST"
VL_IPI = "VL_IPI"
NOME_DEST = "NOME_DEST"
CST = "CST"
ALIQ= "ALIQ"
VL_ITEM= "VL_ITEM"
COD_MOD="COD_MOD"
IND_OPER="IND_OPER"
IND_ESCRI="IND_ESCRI"
nNF = "nNF"
NOME_EMIT = "NOME_EMIT"
xPais_DEST = "xPais_DEST"
xMun_DEST = "xMun_DEST"
xPais_EMIT = "xPais_EMIT"
xMun_EMIT = "xMun_EMIT"



escrituracao = 'EFD_F_X_EFD_C_X_NF-E_(ESCRITURAÇÃO)'
receita = 'EFD_F_X_EFD_C_X_NF-E_(RECEITA)'
CAMINHO_SITUACAO = 'src\\assets\\Situacao_NF-e.xlsx'
CAMINHO_CFOP = 'src\\assets\\XML_CFOPs.xlsx'
CAMINHO_COD_SIT = 'src\\assets\\COD_SIT.xlsx'
json_path = "src\\assets\\registros.json"
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

NFE = { 
        rename_e: 
        {PERÍODO: 'nfeProc_NFe_infNFe_ide_dhEmi',
        ID: 'nfeProc_NFe_infNFe_Id',
        CNPJ_EMIT: 'nfeProc_NFe_infNFe_emit_CNPJ',
        CNPJ_DEST: 'nfeProc_NFe_infNFe_dest_CNPJ',
        SITUACAO:'nfeProc_protNFe_infProt_xMotivo',
        tpNF: 'nfeProc_NFe_infNFe_ide_tpNF',
        CHV_NFE:'nfeProc_protNFe_infProt_chNFe'},

        CAMPOS_ESCRITURACAO:
        ['nfeProc_NFe_infNFe_ide_dhEmi', 
        'nfeProc_NFe_infNFe_Id', 
        'nfeProc_NFe_infNFe_emit_CNPJ', 
        'nfeProc_NFe_infNFe_dest_CNPJ', 
        'nfeProc_protNFe_infProt_xMotivo', 
        'nfeProc_NFe_infNFe_ide_tpNF', 
        'nfeProc_protNFe_infProt_chNFe'],

        rename_r:{
        PERÍODO: 'nfeProc_NFe_infNFe_ide_dhEmi',
        CHV_NFE:'nfeProc_protNFe_infProt_chNFe',
        nNF: 'nfeProc_NFe_infNFe_ide_nNF',
        CNPJ_EMIT: 'nfeProc_NFe_infNFe_emit_CNPJ',
        NOME_EMIT: 'nfeProc_NFe_infNFe_emit_xNome',
        CNPJ_DEST: 'nfeProc_NFe_infNFe_dest_CNPJ',
        SITUACAO:'nfeProc_protNFe_infProt_xMotivo',
        xMun_EMIT: 'nfeProc_NFe_infNFe_emit_enderEmit_xMun',
        xPais_EMIT: 'nfeProc_NFe_infNFe_emit_enderEmit_xPais',
        xMun_DEST:'nfeProc_NFe_infNFe_dest_enderDest_xMun',
        xPais_DEST:'nfeProc_NFe_infNFe_dest_enderDest_xPais'
        },

        CAMPOS_RECEITA:
        ['nfeProc_NFe_infNFe_ide_dhEmi', 
        'nfeProc_protNFe_infProt_chNFe',
        'nfeProc_NFe_infNFe_ide_nNF', 
        'nfeProc_NFe_infNFe_emit_CNPJ',
        'nfeProc_NFe_infNFe_emit_xNome',
        'nfeProc_NFe_infNFe_dest_CNPJ', 
        'nfeProc_protNFe_infProt_xMotivo', 
        'nfeProc_NFe_infNFe_emit_enderEmit_xMun',
        'nfeProc_NFe_infNFe_emit_enderEmit_xPais',
        'nfeProc_NFe_infNFe_dest_enderDest_xMun',
        'nfeProc_NFe_infNFe_dest_enderDest_xPais']
}

C_re_C100 = {
        COD_PART: 'field_8'
}
C_re_0150 = {
        COD_PART: 'field_12',
        NOME_DEST: 'field_13',
        CNPJ_DEST: 'field_15'
}

ICMS_re_C100 = {
        COD_PART: 'field_5'
}
ICMS_re_0150 = {
        COD_PART: 'field_3',
        NOME_DEST: 'field_4',
        CNPJ_DEST: 'field_6'
}


