from .console import run_cmd


def reg_add_cmd(path, key, dtype, dvalue):
    return run_cmd(['reg', 'add', path, '/f', '/v', key, '/t', dtype, '/d', dvalue])


def reg_add(path, key, dtype, dvalue):
    pass