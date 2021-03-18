import socket

import logger
import reactor
import protocol
from db import MessageUDatabase

# Using mixing to divide the logic into subgroups
class RequestHandlerMixin(object):
    def __init__(self):
        self._request_handlers = {
            self._protocol.REQUEST_REGISTER: self._response_register_user,
            self._protocol.REQUEST_LIST_USERS: self._response_user_list,
            self._protocol.REQUEST_READ_MESSAGES: self._response_get_messages,
            self._protocol.REQUEST_SEND_MESSAGE: self._response_send_messages,
            self._protocol.REQUEST_PUBLIC_KEY: self._response_public_key
        }

    def _op_error(self, uid, op, data):
        self._logger.error(f"Error: Invalid op #{op}")
        return self._protocol.RESPONSE_REROR, b""

    def _response_error(self, uid, op, data):
        self._logger.error("Unknown server error occurred")
        return self._protocol.RESPONSE_ERROR, b""

    def _response_register_user(self, uid, op, data):
        uid = self._db.register_user(data["name"], data["public_key"])
        return self._protocol.RESPONSE_REGISTRATION_SUCCESS, {"uid": uid}

    def _response_send_messages(self, uid, op, data):
        self._db.put_user_message(uid, data["recipient"], data["type"], data["content"])
        return self._protocol.RESPONSE_MESSAGE_SENT, {"recipient": data["recipient"], "id": 0}

    def _response_get_messages(self, uid, op, data):
        messages = self._db.pop_user_messages(uid)
        return self._protocol.RESPONSE_PENDING_MESSAGES, messages

    def _response_user_list(self, uid, op, data):
        users = self._db.get_users(uid)
        return self._protocol.RESPONSE_USER_LIST, users

    def _response_public_key(self, uid, op, data):
        public_key = self._db.get_user_public_key(data["uid"])
        import binascii
        binascii.hexlify(data["uid"])
        return self._protocol.RESPONSE_PUBLIC_KEY, public_key


class ChatServer(RequestHandlerMixin):
    def __init__(self, config_file):
        self._PROTOCOL_VERSION = 1
        self._DEFAULT_CONNECTION_BACKLOG = 256
        self._DEFAULT_ADDRESS = "0.0.0.0"
        self._DB_FILE = ".\\server.db"

        self._port = self._read_config(config_file)

        self._db = MessageUDatabase()
        self._protocol = protocol.ProtocolV1()
        
        RequestHandlerMixin.__init__(self)
        self._logger = logger.get_module_logger(__name__)

    def _call_request_handler(self, uid, op, data):
        try:
            handler = self._request_handlers.get(op, self._op_error)
            return handler(uid, op, data)

        except:
            return self._response_error(uid, op, data)

    def _handle_request(self, uid, op, data):
        response_code, payload = self._call_request_handler(uid, op, data)
        return self._protocol.make_response(response_code, payload)

    def _read_config(self, config_file):
        with open(config_file, "r") as config:
            return int(config.read())
    
    ## Reactor callbacks
    def _reactor_recv(self, reactor, client):
        header = client.recv(self._protocol.request_header_size)
        if not header:
            return self._reactor_err(reactor, client)

        uid, op, size = self._protocol.parse_request_header(header)

        payload = client.recv(size)
        data = self._protocol.parse_request_payload(op, payload)

        response = self._handle_request(uid, op, data)
        reactor.put_message(client, response)

    def _reactor_err(self, reactor, client):
        reactor.pop_all_messages(client)
        reactor.unregister_all(client)
        client.close()

    def _reactor_write(self, reactor, client):
        reactor.send_from_queue(client)
        reactor.unregister_all(client)
        client.close()

    def _reactor_accept(self, reactor, server):
        client, __ = server.accept()
        reactor.register(client, reactor.EVENT_RECV, self._reactor_recv)
        reactor.register(client, reactor.EVENT_SEND, self._reactor_write)
        reactor.register(client, reactor.EVENT_ERR, self._reactor_err)

    ## Entry point
    def start(self):
        self._logger.info(f"Starting MessageU Chat Server on {self._DEFAULT_ADDRESS }:{self._port}")

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self._DEFAULT_ADDRESS, self._port))
        server_socket.listen(self._DEFAULT_CONNECTION_BACKLOG)

        self._reactor = reactor.SimpleReactor()
        self._reactor.register(server_socket, reactor.EVENT_RECV, self._reactor_accept)

        # Blocking
        self._reactor.start()

    def stop():
        self._logger.info(f"Stopping MessageU Chat Server")
        self._reactor.stop()
