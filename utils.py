from bson.objectid import ObjectId


def clean_dict_helper(d):
    if isinstance(d, ObjectId):
        return str(d)

    if isinstance(d, list):  # For those db functions which return list
        return [clean_dict_helper(x) for x in d]

    if isinstance(d, dict):
        for k, v in deepcopy(d).items():
            d.update({k: clean_dict_helper(v)})

    return d
