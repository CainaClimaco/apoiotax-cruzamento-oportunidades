import polars as pl
import xml 
from xmltodict import parse
import datatricks.io.file_definitions as dt_fd
import ast
import time
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
                            output_dict[str(prefix+key+separator+str(index)).replace("@", "")] = value

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

def find_key(str_content, keys):
    dict_xml = ast.literal_eval(str_content)
    content = {}
    if keys == []:
          return dict_xml
    for key in keys:
        try: 
            content[key] = dict_xml[key]
        except:
            content[key] = None
    return content 

def file_content(df):
            df_File_Content_Col = df.with_columns(pl.struct(pl.all())
                                                  .map_elements(lambda x: process_content_xml_file(x[dt_fd.FULL_PATH], x[dt_fd.ENCODING]), return_dtype=pl.String)
                                                  .alias(dt_fd.XML_CONTENT))
            return df_File_Content_Col

def extract_columns(df, field_list):
    df = df.with_columns(pl.col(dt_fd.XML_CONTENT).str.replace('"', "").alias(dt_fd.XML_CONTENT))
    df = df.select(dt_fd.XML_CONTENT, 'full_Path', 'file_Name')
    df = df.with_columns(pl.col(dt_fd.XML_CONTENT).map_elements(lambda x: find_key(x, field_list), return_dtype=pl.Struct).alias('new_columns'))
    df = df.unnest('new_columns')
    return df

def conversor_xml(inbound, field_list=[]):
      df = file_content(inbound)
      df = extract_columns(df, field_list)
      return df