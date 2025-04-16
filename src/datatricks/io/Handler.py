import xmltodict

def flatten(input_dict, separator="_", prefix=""):
    output_dict = {}

    for key, value in input_dict.items():

        if isinstance(value, dict) and value:
            deeper = flatten(value, separator, prefix + key + separator)
            output_dict.update({key2: val2 for key2, val2 in deeper.items()})

        elif isinstance(value, list) and value:

            for index, sublist in enumerate(value, start=1):

                if isinstance(sublist, dict) and sublist:
                    deeper = flatten(
                        sublist,
                        separator,
                        prefix + key + separator + str(index) + separator,
                    )
                    output_dict.update({key2: val2 for key2, val2 in deeper.items()})

                else:
                    output_dict[prefix + key + separator + str(index)] = value

        else:
            output_dict[prefix + key] = value
    return output_dict


def is_odd_file(data):
    field_name = next(iter(data))
    if field_name.split("_")[0] in file_types:
        return True

    return False


def build_column_name(lst, start_index):
    temp = []
    dict_output = {}
    dig_list = []
    for element in lst:
        if not str(element).isdigit():
            temp.append(element)
        else:
            if (temp[len(temp) - 1] != "det") and (len(dig_list) == 0):
                dig_list.append("1")
                dig_list.append(element)
            else:
                dig_list.append(element)
    temp = temp[-3:]
    start = temp[0]
    for element in temp[1:]:
        start += "_" + element
    try:
        try:
            return start, dig_list[0], dig_list[1]
        except:
            return start, dig_list[0]
    except:
        return start


def count_repeated_fields(details_dict):
    det_list = []
    rastro_list = []
    for key, value in details.items():
        if isinstance(key, tuple):
            if len(key) == 3:
                if key[1] not in det_list:
                    det_list.append(key[1])
                if key[2] not in rastro_list:
                    rastro_list.append(key[2])
            if len(key) == 2:
                if key[1] not in det_list:
                    det_list.append(key[1])
                    rastro_list = ["1"]
        else:
            det_list = ["1"]
            rastro_list = ["1"]
    return det_list, rastro_list


def detail_items(details, det_list, rastro_list):
    delete_detail_items_list = []
    detail_items_list = []

    if len(rastro_list) <= 1:
        for det in det_list:
            detail_items_dict = {}
            for key, value in details.items():
                if (isinstance(key, tuple)) and (key[1] == det):
                    detail_items_dict[key[0]] = value[0]
                elif not isinstance(key, tuple):
                    detail_items_dict[key] = value[0]
            detail_items_list.append(detail_items_dict)
        return detail_items_list, delete_detail_items_list

    elif len(rastro_list) > 1:
        for det in det_list:
            detail_items_dict = {}
            for key, value in details.items():
                if (isinstance(key, tuple)) and (len(key) == 3):
                    if key[0] not in delete_detail_items_list:
                        delete_detail_items_list.append(key[0])
                elif (isinstance(key, tuple)) and (len(key) == 2):
                    if (len(det_list) == 1) and (
                        key[0] not in delete_detail_items_list
                    ):
                        delete_detail_items_list.append(key[0])
                    elif (len(det_list) > 1) and (key[1] == det):
                        detail_items_dict[key[0]] = value[0]
                elif not isinstance(key, tuple):
                    detail_items_dict[key] = value[0]

            detail_items_list.append(detail_items_dict)

        return detail_items_list, delete_detail_items_list

def get_all_data(path):
    with open(path, encoding="utf-8") as fd:
        return flatten(xmltodict.parse(fd.read()))
