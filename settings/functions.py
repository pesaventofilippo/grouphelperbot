import settings

def getStr(string, args=None):
    import importlib
    try:
        locale = importlib.import_module("settings.lang_"+settings.settings.Bot.language)
    except ImportError:
        locale = settings.lang_en
    if string in locale.dict:
        if args == None:
            return locale.dict[string]
        else:
            return locale.dict[string].format(*args)
    else:
        return "Not found"
