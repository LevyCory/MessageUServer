import logging
from logging import handlers

# Not thread safe, do not use with threads!

_g_cmd_verbose_level = logging.INFO
_g_file_logging_level = logging.DEBUG

def set_cmd_level(level):
    _g_cmd_verbose_level = level

def get_module_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(_g_cmd_verbose_level)

    cmd_handler = logging.StreamHandler()
    cmd_formatter = logging.Formatter('%(levelname)s: %(message)s')
    cmd_handler.setFormatter(cmd_formatter)
    cmd_handler.setLevel(_g_cmd_verbose_level)
    logger.addHandler(cmd_handler)

    file_handler = handlers.TimedRotatingFileHandler("chatserver.log", backupCount=5, delay=True)
    file_formatter = logging.Formatter('%(levelname)s [%(asctime)s] %(name)s: %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(_g_file_logging_level)
    logger.addHandler(file_handler)

    return logger
