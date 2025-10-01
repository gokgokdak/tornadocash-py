import datetime
import multiprocessing as MP
import os
import sys
import threading as TR
from enum import Enum
from multiprocessing.synchronize import Lock as MPLock
from typing import Any, TextIO

import util
from mytype import MBytes, Second


class Level(Enum):
    INFO  = 'I'
    ERROR = 'E'
    WARN  = 'W'
    DEBUG = 'D'


class Color(Enum):
    NONE   = 'NONE'
    RED    = 'RED'
    GREEN  = 'GREEN'
    YELLOW = 'YELLOW'
    BLUE   = 'BLUE'
    PURPLE = 'PURPLE'
    CYAN   = 'CYAN'
    GREY   = 'GREY'


class Style(Enum):
    NONE      = 'NONE'
    BOLD      = 'BOLD'
    LIGHT     = 'LIGHT'
    ITALIC    = 'ITALIC'
    UNDERLINE = 'UNDERLINE'


class STDOutStreamWrapper(object):

    def __init__(self, stream: TextIO):
        self.mutex : TR.Lock = TR.Lock()
        self.stream: TextIO  = stream

    def write(self, buf: str):
        with self.mutex:
            self.stream.write(buf)

    def writelines(self, lines: list[str]):
        with self.mutex:
            self.stream.writelines(lines)

    def flush(self):
        with self.mutex:
            self.stream.flush()


def get_console_rich_text(line: str, color: Color, style: Style = Style.NONE) -> str:
    style_code: str = ''
    if style == Style.BOLD:
        style_code = '1;'
    elif style == Style.LIGHT:
        style_code = '2;'
    elif style == Style.ITALIC:
        style_code = '3;'
    elif style == Style.UNDERLINE:
        style_code = '4;'
    if color == Color.RED:
        return f'\033[{style_code}31m{line}\033[0m'
    elif color == Color.GREEN:
        return f'\033[{style_code}32m{line}\033[0m'
    elif color == Color.YELLOW:
        return f'\033[{style_code}33m{line}\033[0m'
    elif color == Color.BLUE:
        return f'\033[{style_code}34m{line}\033[0m'
    elif color == Color.PURPLE:
        return f'\033[{style_code}35m{line}\033[0m'
    elif color == Color.CYAN:
        return f'\033[{style_code}36m{line}\033[0m'
    elif color == Color.GREY:
        return f'\033[{style_code}90m{line}\033[0m'
    else:
        style_code = style_code[:-1]
        return f'\033[{style_code}m{line}\033[0m'


STDOUT: STDOutStreamWrapper = STDOutStreamWrapper(sys.stdout)
STDERR: STDOutStreamWrapper = STDOutStreamWrapper(sys.stderr)
LEVEL_COLOR: dict[Level, Color] = {
    Level.INFO : Color.GREEN,
    Level.ERROR: Color.RED,
    Level.WARN : Color.YELLOW,
    Level.DEBUG: Color.GREY
}
LEVEL_ORDER: list[Level] = [Level.DEBUG, Level.INFO, Level.WARN, Level.ERROR]


class Logger(object):
    def __init__(self, directory: str, name: str, rotate_size: MBytes = 0, write_interval: Second = Second(0)):
        os.makedirs(directory, exist_ok=True)
        self.directory  : str       = directory
        self.name       : str       = name
        self.first_file : bool      = True
        self.file       : TextIO    = self.open_file()
        self.cache      : list[str] = []
        self.interval   : Second    = write_interval
        self.timestamp  : Second    = Second(0)
        self.min_level  : Level     = Level.INFO
        self.stdout     : bool      = False
        self.mutex      : MPLock    = MP.Lock()
        self.rotate_size: MBytes    = rotate_size

    def __del__(self):
        self.file.close()

    def console(self, enable: bool) -> None:
        with self.mutex:
            self.stdout = enable

    def set_level(self, level: Level) -> None:
        with self.mutex:
            if level not in Level:
                raise ValueError(f'Invalid log level: {level}')
            self.min_level = level

    def get_level(self) -> Level:
        with self.mutex:
            return self.min_level

    def log(self, level: Level, tag: str, message: str|list[str], color: Color, style: Style, filename: str|None, line_number: int|None) -> None:
        if LEVEL_ORDER.index(level) < LEVEL_ORDER.index(self.min_level):
            return
        now: Second = util.unix_timestamp()
        if 0 == self.timestamp:
            self.timestamp = now
        with self.mutex:
            # Check input type
            if not isinstance(message, str) and not isinstance(message, list):
                STDOUT.write(f'log() message is not str or list: {message}\n')
                return
            if not isinstance(message, list):
                message = [message]
            # Process message
            processed_console: list[str] = []
            processed_write  : list[str] = []
            for msg in message:
                date_and_precise_time = lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')[:-3]
                console_color = LEVEL_COLOR[level] if color == Color.NONE else color
                text_console: str = f'[{level.value} {date_and_precise_time()} tid={TR.get_native_id()} {tag}] {get_console_rich_text(msg, console_color, style)}'
                text_write  : str = f'[{level.value} {date_and_precise_time()} tid={TR.get_native_id()} {tag}] {msg}'
                if filename is not None and line_number is not None:
                    location: str = f' ({filename}:{line_number})'
                    text_console += get_console_rich_text(location, console_color, style)
                    text_write   += location
                processed_console.append(f'{text_console}\n')
                processed_write.append(f'{text_write}\n')
            # Console print
            if self.stdout:
                STDOUT.writelines(processed_console)
            # Write
            self.cache.extend(processed_write)
            if 0 == self.interval or now - self.timestamp >= self.interval:
                self.file.writelines(self.cache)
                self.timestamp = now
                self.cache.clear()
            # Rotate log file
            if 0 != self.rotate_size and self.file_size() >= self.rotate_size:
                self.file.close()
                self.file = self.open_file()
    
    def file_size(self) -> MBytes:
        return MBytes(int(os.fstat(self.file.fileno()).st_size / 1024.0 / 1024.0))
    
    def open_file(self) -> TextIO:
        date_and_time = lambda: datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename: str = f'{self.name}_{date_and_time()}'
        if self.name == '':
            filename = date_and_time()
        if self.first_file:
            self.first_file = False
            filename = f'{filename}_start'
        return open(file=f'{self.directory}/{filename}.log', mode='a', buffering=1)

    def force_write(self) -> None:
        with self.mutex:
            if self.cache:
                self.file.writelines(self.cache)
                self.cache.clear()


class Instance:

    initialized: bool = False
    obj: Logger|None = None

    @classmethod
    def init(cls, directory: str, name: str, rotate_size: MBytes = 0, write_interval: Second = Second(0)) -> bool:
        if Instance.initialized:
            return False
        Instance.obj = Logger(directory, name, rotate_size, write_interval)
        Instance.initialized = True
        return True

    @classmethod
    def un_init(cls) -> bool:
        if Instance.initialized:
            Instance.obj.force_write()
            Instance.obj = None
            Instance.initialized = False
            return True
        return False

    @classmethod
    def set_console_enable(cls, enable: bool) -> None:
        if Instance.obj is None:
            return
        Instance.obj.console(enable)

    @classmethod
    def set_level(cls, level: Level) -> None:
        if Instance.obj is None:
            return
        if level not in Level:
            raise ValueError(f'Invalid log level: {level}')
        Instance.obj.set_level(level)

    @classmethod
    def get_level(cls) -> Level:
        if Instance.obj is None:
            return Level.INFO
        return Instance.obj.get_level()

    @classmethod
    def info(cls, tag: str, message: str|list[str], color: Color, style: Style, filename: str|None, line_number: int|None) -> None:
        if Instance.obj is None:
            return
        Instance.obj.log(Level.INFO, tag, message, color, style, filename, line_number)

    @classmethod
    def error(cls, tag: str, message: str|list[str], color: Color, style: Style, filename: str|None, line_number: int|None) -> None:
        if Instance.obj is None:
            return
        Instance.obj.log(Level.ERROR, tag, message, color, style, filename, line_number)

    @classmethod
    def warn(cls, tag: str, message: str|list[str], color: Color, style: Style, filename: str|None, line_number: int|None) -> None:
        if Instance.obj is None:
            return
        Instance.obj.log(Level.WARN, tag, message, color, style, filename, line_number)

    @classmethod
    def debug(cls, tag: str, message: str|list[str], color: Color, style: Style, filename: str|None, line_number: int|None) -> None:
        if Instance.obj is None:
            return
        Instance.obj.log(Level.DEBUG, tag, message, color, style, filename, line_number)


"""
Fake file-like stream object that redirects writes to a logger instance.
"""
class STDOutStreamRelay(object):

    def __init__(self, level: str):
        self.mutex   : MPLock = MP.Lock()
        self.level   : str    = level
        self.buffer  : str    = ''

    def flush(self):
        pass

    def write(self, buf: Any):
        text   : str = str(buf)
        reserve: bool = not text.endswith('\n')
        with self.mutex:
            # Append buffer
            self.buffer += str(buf)
            # Remove '\n' at the end of buffer, because it will cause an extra '' in variable lines
            if self.buffer.endswith('\n'):
                self.buffer = self.buffer[:-1]
            # Split buffer into lines by '\n'
            lines: list[str] = self.buffer.split('\n')
            lines = [line.strip('\n') for line in lines]
            # Reserve last line if it is not a completed line
            if reserve:
                self.buffer = lines.pop(len(lines) - 1)
            else:
                self.buffer = ''
        if 'I' == self.level:
            Instance.info('stdout', lines, Color.NONE, Style.NONE, None, None)
        elif 'E' == self.level:
            Instance.error('stderr', lines, Color.NONE, Style.NONE, None, None)
        elif 'W' == self.level:
            Instance.warn('stdout', lines, Color.NONE, Style.NONE, None, None)
        elif 'D' == self.level:
            Instance.debug('stdout', lines, Color.NONE, Style.NONE, None, None)


def init(directory: str, name: str = '', rotate_size: MBytes = 0, write_interval: Second = Second(0)) -> bool:
    sys.stdout = STDOutStreamRelay('I')
    sys.stderr = STDOutStreamRelay('E')
    return Instance.init(directory, name, rotate_size, write_interval)


def un_init() -> bool:
    succeed: bool = Instance.un_init()
    if succeed:
        sys.stdout = STDOUT
        sys.stderr = STDERR
    return succeed


def set_console_enable(enable: bool) -> None:
    Instance.set_console_enable(enable)


def set_level(level: Level):
    Instance.set_level(level)


def get_level() -> Level:
    return Instance.get_level()


@util.caller_location
def info(tag: str, message: str|list[str], color: Color = Color.NONE, style: Style = Style.NONE, filename: str = None, line_number: int = None) -> None:
    if filename is None or line_number is None:
        raise Exception('Log.Info() filename or line_number is None')
    Instance.info(tag, message, color, style, filename, line_number)


@util.caller_location
def error(tag: str, message: str|list[str], color: Color = Color.NONE, style: Style = Style.NONE, filename: str = None, line_number: int = None) -> None:
    if filename is None or line_number is None:
        raise Exception('Log.Error() filename or line_number is None')
    Instance.error(tag, message, color, style, filename, line_number)


@util.caller_location
def warn(tag: str, message: str|list[str], color: Color = Color.NONE, style: Style = Style.NONE, filename: str = None, line_number: int = None) -> None:
    if filename is None or line_number is None:
        raise Exception('Log.Warn() filename or line_number is None')
    Instance.warn(tag, message, color, style, filename, line_number)


@util.caller_location
def debug(tag: str, message: str|list[str], color: Color = Color.NONE, style: Style = Style.NONE, filename: str = None, line_number: int = None) -> None:
    if filename is None or line_number is None:
        raise Exception('Log.Debug() filename or line_number is None')
    Instance.debug(tag, message, color, style, filename, line_number)


def console(message: str|list[str]) -> None:
    if isinstance(message, str):
        STDOUT.write(f'{message}\n')
    elif isinstance(message, list):
        for msg in message:
            STDOUT.write(f'{msg}\n')
