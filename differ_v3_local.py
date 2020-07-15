import pprint as pp

def check_skip_do_is_bool(input):
    if not isinstance(input, bool):
        raise ValueError('"skip_do" must be a boolean value.')


def check_skip_do_paths(paths, prior_key):
    if paths is False:
        return None
    elif isinstance(paths, dict):
        for k in paths:
            check_skip_do_paths(paths[k], define_path(prior_key, k))
        return None
    else:
        raise ValueError(
            "skip_do_paths is not structured properly, problem at {} : {}".format(prior_key, paths)
        )


def count(model, skip_do, skip_do_paths=None, prior_key=''):
    check_skip_do_is_bool(skip_do)
    if skip_do_paths is None:
        skip_do_paths = {}
    check_skip_do_paths(skip_do_paths, prior_key)
    if skip_do:
        return c_include(model, prior_key, skip_do_paths)
    else:
        return c_exclude(model, prior_key, skip_do_paths)


def c_include(model, prior_key, skip_do_paths, path=''):
    """
    1) follow skip do paths
    2) raise warning if skip_do leads to a path that isn't present.
    """

    return None


def define_path(prior_path, next_key):
    if len(prior_path) == 0:
        return next_key
    else:
        return prior_path + "." + next_key


def c_exclude(model, prior_key, skip_do_paths, check_following=True, path=''):
    if prior_key in skip_do_paths:
        if isinstance(skip_do_paths[prior_key], dict):
            # ! will this create issues with identically named keys in different parts of the model?
            skip_do_paths.update(skip_do_paths[prior_key])
        else:
            check_following = False

    if (isinstance(model, dict) and "new" in model and "old" in model
            and check_following):
        return {'field_count': 1, 'error_data': {path: model}}
    elif model is None and check_following is True:
        return {'field_count': 1, 'error_data': {}}
    elif model is False and check_following is True:
        return {'field_count': 0, 'error_data': {}}
    elif isinstance(model, dict):
        temp_dict = {'field_count': 0, 'error_data': {}}
        for key in model:
            temp_count_dict = c_exclude(model[key], key, skip_do_paths, check_following,
                                        define_path(path, key))
            temp_dict['field_count'] += temp_count_dict['field_count']
            temp_dict['error_data'].update(temp_count_dict['error_data'])
        return temp_dict
    elif isinstance(model, list):
        temp_dict = {'field_count': 0, 'error_data': {}}
        for index, item in enumerate(model):
            temp_count_dict = c_exclude(item, index, skip_do_paths, check_following,
                                        define_path(path, str(index)))
            temp_dict['field_count'] += temp_count_dict['field_count']
            temp_dict['error_data'].update(temp_count_dict['error_data'])
        return temp_dict
    elif not check_following:
        return {'field_count': 0, 'error_data': {}}
    else:
        print('the impossible error!')
        pp.pprint(model)
        return {'field_count': 0, 'error_data': {}}


def collapse(obj, flds_to_add, paths):
    flds_to_add.update({x[0]: x[1] for x in obj.items() if x[0] not in paths})
    next_call = next((x for x in obj.items() if x[0] in paths), None)
    if next_call is None:
        return list()
    elif paths.get(next_call[0], True) == False:
        return_list = [dict(item, **flds_to_add) for item in next_call[1]]
        return return_list
    else:
        return_list = []
        for item in next_call[1]:
            return_list += collapse(item, flds_to_add, paths[next_call[0]])
        return return_list


def union_of_keys(new, old):
    new_keys = {k for k in new} if isinstance(new, dict) else set()
    old_keys = {k for k in old} if isinstance(old, dict) else set()
    return new_keys & old_keys

def diff_dict(new, old, list_mgmt, collapse_paths):
    keys = union_of_keys(new, old)
    return {
                key: differ(
                            new.get(key), old.get(key),
                            key, list_mgmt, collapse_paths
                            )
                for key in keys}

def diff_leaf(new, old):
    return None if new == old else {"new": new, "old": old}

def collapse_list(diff_list, collapse_key):
    if not old:
        return None
    else:
        return [
                collapse(item, {}, collapse_key)
                for item in diff_list
                ]

def get_keys_from_list_with_key(new, old, field_name):
    new_keys = {k.get(field_name, None) for k in new} if isinstance(new, list) else set()
    old_keys = {k.get(field_name, None) for k in old} if isinstance(old, list) else set()
    return new_keys & old_keys


def diff_list_with_key(new, old, field_name, ):
    keys = get_keys_from_list_with_key(new, old, field_name)
    # this is testing if there is a missing key, would be better to be able to pass
    if None in keys or "" in keys or " " in keys:
        # print("There was a missing key in the list at ", prior_key)
        return False
    else:
        temp_dict = {}
        for key in keys:
            new_item = next(
                (x for x in new if x[field_name] == key), None)
            old_item = next(
                (x for x in old if x[field_name] == key), None)
            temp_dict.update({key: differ(new_item, old_item, key,
                                          list_mgmt, collapse_paths)})
        return temp_dict

def diff_list(new, old, prior_key, list_mgmt, collapse_paths):
    if prior_key in collapse_paths:
        if old:
            old = collapse_list(old, collapse_paths[prior_key])
        if new:
            new = collapse_list(new, collapse_paths[prior_key])

    key_and_keyed = list_mgmt.get(prior_key, None)
    if isinstance(key_and_keyed, type(None)):
        return False
    elif key_and_keyed['keyed'] is True:
        return diff_list_with_key(new, old, key_and_keyed['field'])
    else:
        fld_name = key_and_keyed['field']
        new_jst_d_flds = [x.get(fld_name, None) for x in new]
        old_jst_d_flds = [x.get(fld_name, None) for x in old]
        shared = list({x for x in new_jst_d_flds if x in old_jst_d_flds})
        for item in shared:
            if item in new_jst_d_flds:
                new_jst_d_flds.remove(item)
            if item in old_jst_d_flds:
                old_jst_d_flds.remove(item)
        shared_components = [None for x in shared]
        if len(old_jst_d_flds) > len(new_jst_d_flds):
            new_jst_d_flds += [None for x in
                               range(len(old_jst_d_flds) - len(new_jst_d_flds))]
        else:
            old_jst_d_flds += [None for x in
                               range(len(new_jst_d_flds) - len(old_jst_d_flds))]

        disjoint_components = [
            {"new": new_jst_d_flds[i], "old": old_jst_d_flds[i]}
            for i in range(len(new_jst_d_flds))]
        return shared_components + disjoint_components


def differ(new, old, prior_key, list_mgmt={}, collapse_paths={}):
    if isinstance(new, dict) or isinstance(old, dict):
        return diff_dict(new, old, list_mgmt, collapse_paths)
    elif isinstance(new, list) or isinstance(old, list):
        return diff_list(new, old, prior_key, list_mgmt, collapse_paths)
    else:
        return diff_leaf(new, old)
