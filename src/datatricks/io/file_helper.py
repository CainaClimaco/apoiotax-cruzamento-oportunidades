import os
import hashlib
import shutil
import polars as pl
import chardet
import magic
from datatricks.sped.file_identifier import is_XML, is_pipedFile
from datatricks.sped.file_identifier import is_expected_type, is_efdc, is_efdf
import datatricks.io.file_definitions as fd


def get_all_file_data(full_Path):
    df = get_files(full_Path)
    df = df.with_columns(
        pl.col(fd.FULL_PATH).map_elements(get_file_type, return_dtype=pl.String).alias(fd.F_TYPE)
    )
    df = df.with_columns(
        pl.col(fd.FULL_PATH)
        .map_elements(get_file_encode_brute_force, return_dtype=pl.String)
        .alias(fd.ENCODING)
    )
    df = df.with_columns(
        pl.col(fd.FULL_PATH).map_elements(get_md5, return_dtype=pl.String).alias(fd.MD5)
    )
    grouped_df = (
        df.group_by(fd.MD5)
        .agg([pl.count(fd.FULL_PATH).alias("count")])
        .sort("count", descending=True)
        .filter(pl.col("count") > 1)
    )
    df = df.with_columns(pl.col(fd.MD5).map_elements(lambda x: x in grouped_df[fd.MD5].to_list(), return_dtype=pl.Boolean).alias(fd.IS_DUPLICATED))

    return df


def get_sped_filters(df):
    
    df = df.with_columns(df.map_rows(lambda x : get_file_content_by_type(x[0], x[2], x[3]), return_dtype=pl.String))
    df = df.rename({'map': fd.F_CONTENT})
    df = df.with_columns(pl.col(fd.F_CONTENT).map_elements(lambda x: is_XML(x, special_identifier="cteProc"), return_dtype=pl.Boolean).alias(fd.IS_CTE))
    df = df.with_columns(pl.col(fd.F_CONTENT).map_elements(lambda x: is_XML(x, special_identifier="nfeProc"), return_dtype=pl.Boolean).alias(fd.IS_NFE))
    df = df.with_columns(pl.col(fd.F_CONTENT).map_elements(lambda x: is_XML(x, special_identifier="Reinf"), return_dtype=pl.Boolean).alias(fd.IS_REINF))
    df = df.with_columns(pl.col(fd.F_CONTENT).map_elements(lambda x: is_pipedFile(x, special_identifier="|0000|"), return_dtype=pl.Boolean).alias(fd.IS_PIPPED))
    df = df.with_columns(df.map_rows(lambda x : is_expected_type(x, "0000", 2, "LECD"), return_dtype=pl.Object))
    df = df.rename({'map': fd.IS_ECD})
    df = df.with_columns(df.map_rows(lambda x : is_expected_type(x, "0000", 2, "LECF"), return_dtype=pl.Object))
    df = df.rename({'map': fd.IS_ECF})
    df = df.with_columns(df.map_rows(lambda x : is_efdc(x), return_dtype=pl.Object))
    df = df.rename({'map': fd.IS_EFDC})
    df = df.with_columns(df.map_rows(lambda x : is_efdf(x), return_dtype=pl.Object))
    df = df.rename({'map': fd.IS_EFDF})
    df = df.with_columns(pl.col(fd.FULL_PATH).str.ends_with("pdf").alias(fd.IS_PDF))

    return df


def get_files(path):

    file_name = []
    file_path = []

    for root, _, filenames in os.walk(path):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            try:
                filename_encoded = os.fsdecode(filename)
            except UnicodeDecodeError:
                filename_encoded = filename

            file_name.append(filename_encoded)
            file_path.append(full_path)

    return pl.DataFrame({fd.FULL_PATH: file_path, fd.FILE_NAME: file_name})


def get_file_size(path):
    size = os.path.getsize(path)
    return size


def get_md5(fname):
    hasher = hashlib.md5()
    with open(fname, "rb") as f:
        buff = f.read()
        hasher.update(buff)
        return str(hasher.hexdigest())


def get_file_encode_brute_force(fullPath):
    resp = magic.Magic(mime_encoding=True).from_file(fullPath)
    if resp.startswith("cannot"):
        return get_file_encoding(fullPath)
    
    return resp


def get_file_encoding(fullPath):
    with open(fullPath, 'rb') as f:
        bytes_to_read = os.path.getsize(fullPath) // 10
        result = chardet.detect(f.read(bytes_to_read))
        if result['encoding'] is None:
            result = chardet.detect(f.read())
    return result['encoding']


def get_file_type(fullPath):
    return magic.Magic(mime=True).from_file(fullPath)


def get_simple_files(path):
    resp = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            resp.append(str(os.path.join(root, filename)))
    return resp

def assert_file_encoding(path, encoding):

    default_file_encoding = 'latin-1'
    allowed_exts = ["xml", "txt", "json"]
    extension = path.split('.')[-1]
    path = os.path.normpath(os.fsdecode(path))

    if extension not in allowed_exts:
        return None
    if encoding is None and extension in allowed_exts:
        encoding = default_file_encoding

    if encoding.startswith('unknown') or encoding.startswith('binary'):
        encoding = default_file_encoding

    return encoding


def get_file_content_by_type(path, type,file_encoding):

    resp = assert_file_encoding(path, file_encoding)
    if resp is not None:
        return read_text_file(path,  resp, n_lines=20)
   
    return ""


def read_text_file(path, file_encoding, n_lines=20):
    '''Reads the first n_lines of a text file'''	

    file_content = ""
    try:
        with open(path, 'r', encoding=file_encoding) as f:
            for i in range(n_lines):
                file_content += f.readline()
    
    except UnicodeDecodeError:
        with open(path, 'r', encoding="latin-1") as f:
            for i in range(n_lines):
                file_content += f.readline()
    return file_content


def prepare_output_template(template_path="", output_path="", project_name="Project"):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    shutil.copy(template_path, output_path)
    base_name = os.path.basename(template_path)
    new_name = output_path+project_name+'.'+base_name.split(".")[-1]
    os.rename(output_path+base_name, new_name)
    return new_name
