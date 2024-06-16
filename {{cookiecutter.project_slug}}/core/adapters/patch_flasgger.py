import builtins
import json as json_provider

original_import = builtins.__import__


def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "flask.json" and "JSONEncoder" in fromlist:
        return json_provider
    return original_import(name, globals, locals, fromlist, level)


builtins.__import__ = custom_import
