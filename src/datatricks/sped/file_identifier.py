
import datatricks.io.file_definitions as fd

def is_XML(file_content, special_identifier):
    if file_content is not None:
        return (file_content.startswith('<?xml') 
                or file_content.startswith('<nfeProc')
                or file_content.startswith('<cteProc')
                or file_content.startswith('<Reinf')) and (special_identifier in file_content)
    
    else:
        return False
    
def is_JSON(file_content,special_identifier):
    if file_content is not None:
        return file_content.startswith('{') and special_identifier in file_content
    else:
        return False

def is_efdf(row):
    if row[fd.INDEX_IS_PIPPED] and  not row[fd.INDEX_IS_ECF] and not row[fd.INDEX_IS_ECD]:
        for line in row[fd.INDEX_F_CONTENT].split('\n'):
            if "|0000|" in line:
                if check_if_is_date(line.split("|")[4].replace(" ","")):
                    return True
                else:
                    return False
    return False


def check_if_is_date(dt):
    if len(dt) == 8 and dt.isdigit():
        if int(dt[0:2]) <= 31 and int(dt[2:4]) <= 12 and int(dt[4:8]) <= 9999:
            return True
        else:
            return False
    else:
        return False


def is_efdc(row):
    if row[fd.INDEX_IS_PIPPED] and not row[fd.INDEX_IS_ECF] and not row[fd.INDEX_IS_ECD]:
        for line in row[fd.INDEX_F_CONTENT].split('\n'):
            if "|0000|" in line:
                if check_if_is_date(line.split("|")[6].replace(" ","")):
                    return True
                else:
                    return False
    return False




def is_pipedFile(file_content, special_identifier):
    if file_content is not None or len(file_content) > 0:
        return file_content.startswith('|0000|') 
    else:
        return False


def is_expected_type(row, register, position, rType):
    resp = get_field_by_recordID(row, register, position)
    if resp == rType:
        return True
    else:
        return False


def get_field_by_recordID(row, record, position):
    if row[fd.INDEX_F_CONTENT] is None or len(row[fd.INDEX_F_CONTENT]) == 0:
        return ""
    if row[fd.INDEX_IS_PIPPED]:
        for line in row[fd.INDEX_F_CONTENT].split('\n'):
            if line.count('|') >= 2:
                fields = line.split('|')
                record_sequence = fields[1]
                if record_sequence == record:
                    return fields[position]
    elif is_XML(row[fd.INDEX_F_CONTENT], 'cteProc') :
        return extract_id(row, fd.INDEX_IS_CTE, "cteProc", "versao=")

    elif is_XML(row[6], 'nfeProc'):
        return extract_id(row, fd.INDEX_IS_NFE, "nfeProc", "versao=")

    return ""


def extract_id(row, flag, special_identifier, key):
    if row[flag]:
        for line in row[fd.INDEX_F_CONTENT].split('\n'):
            if special_identifier in line and key in line:
                return line.split(key)[1].split('"')[1]
        return 0
    else:
        return 0


file = fd.FILE_NAME

def is_Fiscal(file):
    if file is not None and file.startswith('EFD F'):
        return True
    return False   


def is_Contribuicoes(file):
    if file is not None and file.startswith('EFD C'):
        
        return True
    else:
        return False
    
    
def is_NFe(file):
    if file is not None and file.startswith('Conversor'):
        return True
    else:
        return False