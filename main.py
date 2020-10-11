import sys
import server
import client

dargs = {
    "-s": [False],
    "-a": ["127.0.0.1"],
    "--fps": [False],
}

def log(func):
    def log(*args, **kwargs):
        res = func(*args, **kwargs)
        print(func.__name__, args, kwargs, res)
        return res
    return log

def get_arg(parameter, l=1):
    try:
        index = sys.argv.index(parameter)
    except ValueError:
        return False
    try:
        return [sys.argv[index + i] for i in range(l + 1)]
    except IndexError:
        return False

def arg(param: str):
    if param in dargs:
        a = a if (a := get_arg(param, l=len(dargs[param])-1)) else dargs[param]
        return a[0] if len(a) == 1 else a[1:]

if arg("-s"):
    server.main(repopulate=bool(arg("--repop")))
else:
    client.main(arg("-a"))