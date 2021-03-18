import sys
import socket
import select
from queue import Queue

import logger

# Event types
SUPPORTED_EVENTS = {
    "EVENT_RECV": 0,
    "EVENT_SEND": 1,
    "EVENT_ERR": 2
}

def __getattr__(name):
    return SUPPORTED_EVENTS[name]


class SimpleReactor(object):
    _DEFAULT_SELECT_TIMEOUT_MS = 1000

    def __init__(self, verbose=False):
        self._load_event_consts()

        # Map between socket and the data to send to said socket
        self._outbound_connections = []
        self._inbound_connections = []
        self._message_queues = {}
        self._event_handlers = {}

        self._logger = logger.get_module_logger(__name__)

    def _load_event_consts(self):
        for key, value in SUPPORTED_EVENTS.items():
            setattr(self, key, value)

    def _validate_event(self, event):
        if event not in SUPPORTED_EVENTS.values():
            raise ValueError(f"Invalid event type {event}")

    def _empty_handler(reactor, client):
        pass

    def _default_handler_table(self):
        return {value: self._empty_handler for value in SUPPORTED_EVENTS.values()}

    def put_message(self, target, data):
        self._message_queues[target].put_nowait(data)
        self._outbound_connections.append(target)

    def pop_message(self, target):
        return self._message_queues[target].get_nowait()

    def pop_all_messages(self, target):
        messages = []
        while not self._message_queues[target].empty():
            messages.append(self._message_queues[target].get_nowait())

        return messages

    def send_from_queue(self, target):
        msg = self.pop_message(target)
        target.send(msg)
        if self._message_queues[target].empty():
            self._outbound_connections.remove(target)

    def register(self, sock, event, callback):
        self._validate_event(event)

        if sock not in self._event_handlers:
            self._event_handlers[sock] = self._default_handler_table()
            self._message_queues[sock] = Queue()
            self._inbound_connections.append(sock)

        self._event_handlers[sock][event] = callback
        self._logger.debug("Connection registered")

    def unregister(self, sock, event):
        self._validate_event(event)

        if sock not in self._event_handlers:
            raise ValueError("Socket is not registered to this reactor")

        self._event_handlers[sock][event] = self._empty_handler
        self._logger.debug("Connection unregistered")

    def unregister_all(self, sock):
        if sock not in self._event_handlers:
            raise ValueError("Socket is not registered to this reactor")

        del self._event_handlers[sock]
        del self._message_queues[sock]

        if sock in self._inbound_connections:
            self._inbound_connections.remove(sock)
        if sock in self._outbound_connections:
            self._outbound_connections.remove(sock)

    def start(self, timeout=_DEFAULT_SELECT_TIMEOUT_MS):
        self._logger.debug("Startring SimpleReactor")

        while True:
            try:
                read_ready, write_ready, err_ready = select.select(self._inbound_connections,
                                                                   self._outbound_connections,
                                                                   self._inbound_connections,
                                                                   timeout)

                for sock in err_ready:
                    self._event_handlers[sock][self.EVENT_ERR](self, sock)
                for sock in read_ready:
                    self._event_handlers[sock][self.EVENT_RECV](self, sock)
                for sock in write_ready:
                    self._event_handlers[sock][self.EVENT_SEND](self, sock)

            except Exception as exception:
                self._logger.error(exception)

    def stop():
        self._logger.debug("Stopping SimpleReactor")

        for sock in self._inbound_connections:
            try:
                sock.close()
            except:
                # Best effort
                pass
