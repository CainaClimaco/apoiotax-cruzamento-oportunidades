import polars as pl
import xml 
from xmltodict import parse
import datatricks.io.file_definitions as dt_fd
import ast
import re


def flatten(input_dict, separator='_', prefix=''):
            output_dict = {}

            for key, value in input_dict.items():

                if isinstance(value, dict) and value:
                    deeper = flatten(value, separator, prefix+key+separator)
                    output_dict.update({str(key2).replace("@", ""): val2 for key2, val2 in deeper.items()})

                elif isinstance(value, list) and value:

                    for index, sublist in enumerate(value, start=1):

                        if isinstance(sublist, dict) and sublist:
                            deeper = flatten(sublist, separator, prefix+key+separator+str(index)+separator)
                            output_dict.update({str(key2).replace("@", ""): val2 for key2, val2 in deeper.items()})

                        else:
                            if value != None:
                                output_dict[str(prefix+key+separator+str(index)).replace("@", "")] = value.replace("'", "")
                            else:
                                output_dict[str(prefix+key+separator+str(index)).replace("@", "")] = value

                else:
                    if value != None:
                        output_dict[str(prefix+key).replace("@", "")] = value.replace("'", "")
                    else:
                        output_dict[str(prefix+key).replace("@", "")] = value
            return output_dict

def open_xml_file(full_Path, file_Encoding):
            with open(full_Path, encoding=file_Encoding) as content:
                return content.read()

def process_content_xml_file(full_Path, file_Encoding):
            try:
                content = open_xml_file(full_Path, file_Encoding)
                return str(flatten(parse(content), separator='_'))
            except xml.parsers.expat.ExpatError:
                return None


def find_matching_fields(regex_list, dicionario):
    all_keys = set()
    for d in dicionario:
        all_keys.update(d.keys())

    patterns = [re.compile(pattern) for pattern in regex_list]
    return [key for key in all_keys if any(p.fullmatch(key) for p in patterns)]


def find_key(str_content, regex_list, keys):
    dict_xml = ast.literal_eval(str_content)
    content = {}

    if not keys:
        return dict_xml

    for key in keys:
        content[key] = dict_xml.get(key, None)

    matching = find_matching_fields(regex_list, [dict_xml])
    for match in matching:
        content[match] = dict_xml.get(match, None)

    return content

def file_content(df):
            df_File_Content_Col = df.with_columns(pl.struct(pl.all())
                                                  .map_elements(lambda x: process_content_xml_file(x[dt_fd.FULL_PATH], x[dt_fd.ENCODING]), return_dtype=pl.String)
                                                  .alias(dt_fd.XML_CONTENT))            
            return df_File_Content_Col


def extract_columns(df, regex_list, field_list):
    df = df.with_columns(pl.col(dt_fd.XML_CONTENT).str.replace('"', "").alias(dt_fd.XML_CONTENT))
    df = df.select(dt_fd.XML_CONTENT, 'full_Path', 'file_Name')
    
    extracted_data = []
    all_keys = set(field_list)
    for row in df.select(dt_fd.XML_CONTENT).to_series():
        data = find_key(row, regex_list, field_list)
        extracted_data.append(data)
        all_keys.update(data.keys())
    all_keys = sorted(all_keys)
    
    filled_data = []
    for row in extracted_data:
        filled_row = {key: row.get(key, None) for key in all_keys}
        filled_data.append(filled_row)
    
    for key in all_keys:
        df = df.with_columns(pl.Series(name=key, values=[row[key] for row in filled_data]))
    return df



def conversor_xml(inbound, regex_list=[], field_list=[]):
      df = file_content(inbound)
      df = extract_columns(df, regex_list, field_list)
      return df