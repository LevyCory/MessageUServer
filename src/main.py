import sys
import logging

import server
import logger

def main(args):
    if "-v" in args:
        logger.set_cmd_level(logging.DEBUG)

    try:
        srv = server.ChatServer(r".\port.info")
        srv.start()

    except KeyboardInterrupt:
        srv.close()

if __name__ == "__main__":
    main(sys.argv)
