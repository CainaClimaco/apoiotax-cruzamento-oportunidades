import polars as pl
import datatricks.io.file_definitions as fd
from datatricks.io.file_helper import assert_file_encoding

def read_sped_files(df):

    temp_list = []
    cont = 1
    for row in df.iter_rows(named=True):
        f = read_file(full_path=row[fd.FULL_PATH], encoding=row[fd.ENCODING], end_of_file_id="9999")
        f = f.with_columns(id_file = pl.Series([cont]))
        temp_list.append(f)
        cont +=1
    return pl.concat(temp_list)


def read_file(full_path, encoding='latin1', end_of_file_id="9999"):
    
    temp_list = []
    encoding = assert_file_encoding(full_path, encoding)
    if encoding is None:
        return pl.DataFrame()
    try:
        temp_list = basic_file_read(full_path, encoding, end_of_file_id, temp_list)
    except UnicodeDecodeError:
        temp_list = basic_file_read(full_path, "latin1", end_of_file_id, temp_list)

    return pl.DataFrame(temp_list, schema={'consolidado':pl.Utf8, 'file':pl.String}, orient="row")


def basic_file_read(full_path, encoding, end_of_file_id, temp_list):
    temp_list = []
    with open(full_path, 'r', encoding=encoding) as f:
        for line in f:
            if line[1:5] == end_of_file_id:
                temp_list.append([line, full_path])
                break
            else:
                temp_list.append([line, full_path])
    return temp_list

