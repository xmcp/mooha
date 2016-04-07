from ctypes import *
from ctypes.wintypes import *

class COORD(Structure):
    _fields_ = [("X", SHORT),
                ("Y", SHORT)]

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [("Size", COORD),
                ("CursorPosition", COORD),
                ("Attributes", WORD),
                ("Window", SMALL_RECT),
                ("MaximumWindowSize", COORD)]

console = windll.kernel32.GetStdHandle(-11)

def cls():
    s = CONSOLE_SCREEN_BUFFER_INFO()
    windll.kernel32.GetConsoleScreenBufferInfo(console, byref(s))
    cells = DWORD(s.Size.X * s.Size.Y)

    written = DWORD()
    windll.kernel32.FillConsoleOutputCharacterA(console, c_char(b' '), cells, COORD(0, 0), byref(written))
    windll.kernel32.FillConsoleOutputAttribute(console, s.Attributes, cells, COORD(0, 0), byref(written))
    windll.kernel32.SetConsoleCursorPosition(console, COORD(0, 0))

def goto(y, x):
    windll.kernel32.SetConsoleCursorPosition(console, COORD(x, y))

def cll(r, x):
    s = CONSOLE_SCREEN_BUFFER_INFO()
    windll.kernel32.GetConsoleScreenBufferInfo(console, byref(s))
    written = DWORD()
    windll.kernel32.FillConsoleOutputCharacterA(console, c_char(b' '), s.Size.X-x, COORD(x, r), byref(written))

