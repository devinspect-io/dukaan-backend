from bson.objectid import ObjectId
from copy import deepcopy


def change_case(obj, case=None):
    for k in obj.keys():
        if isinstance(obj[k], str):
            obj[k] = obj[k].lower() if case == "lower" else obj[k].title()
    return obj


def clean_dict_helper(d):
    if isinstance(d, ObjectId):
        return str(d)

    if isinstance(d, list):  # For those db functions which return list
        return [clean_dict_helper(x) for x in d]

    if isinstance(d, dict):
        for k, v in deepcopy(d).items():
            if isinstance(v, str):
                v = v.title()
            d.update({k: clean_dict_helper(v)})
    return d
