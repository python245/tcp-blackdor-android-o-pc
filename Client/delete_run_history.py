import ctypes
import sys
from winreg import *
from time import sleep


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if is_admin():
    hKey = OpenKey(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU", 0, KEY_ALL_ACCESS)

    length_of_keys = QueryInfoKey(hKey)
        
    for x in range(0, length_of_keys[1]):
        name, value, key_type = EnumValue(hKey, 0)
        DeleteValue(hKey, name)
        print("{} deleted".format(name))

    CloseKey(hKey)
    sleep(3)
else:
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, sys.argv[0], None, 1)



