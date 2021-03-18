import struct

# Using mixing to divide the logic into subgroups
class PayloadBuilderMixin(object):
    RESPONSE_REGISTRATION_SUCCESS = 1000
    RESPONSE_USER_LIST = 1001
    RESPONSE_PUBLIC_KEY = 1002
    RESPONSE_MESSAGE_SENT = 1003
    RESPONSE_PENDING_MESSAGES = 1004
    RESPONSE_ERROR = 9000

    def __init__(self):
        self._user_list_format = struct.Struct("16s255s")
        self._public_key_response_format = struct.Struct("16s160s")
        self._message_entry_format = struct.Struct("<16sIBI")
        self._message_sent_format = struct.Struct("<16sI")

        self._response_type = {
            self.RESPONSE_REGISTRATION_SUCCESS: self._build_registration_success_response,
            self.RESPONSE_USER_LIST: self._build_user_list_response,
            self.RESPONSE_PUBLIC_KEY: self._build_public_key_response,
            self.RESPONSE_MESSAGE_SENT: self._build_message_sent_response,
            self.RESPONSE_PENDING_MESSAGES: self._build_pending_messages_response,
            self.RESPONSE_ERROR: self._build_error_response
        }

    def _build_registration_success_response(self, data):
        return data["uid"]

    def _build_user_list_response(self, data):
        packed_users = [self._user_list_format.pack(i["uid"], i["name"].encode()) for i in data]
        return b"".join(packed_users)

    def _build_public_key_response(self, data):
        return self._public_key_response_format.pack(data["uid"], data["public_key"])

    def _build_pending_messages_response(self, data):
        packed_messages = []
        for message in data:
            packed_message = self._message_entry_format.pack(message["sender"], message["id"], message["type"], len(message["content"]))
            packed_messages.append(packed_message + message["content"])

        return b"".join(packed_messages)

    def _build_message_sent_response(self, data):
        return self._message_sent_format.pack(data["recipient"], data["id"])

    def _build_error_response(self):
        return b""


class PayloadParserMixin(object):
    REQUEST_REGISTER = 100
    REQUEST_LIST_USERS = 101
    REQUEST_PUBLIC_KEY = 102
    REQUEST_SEND_MESSAGE = 103
    REQUEST_READ_MESSAGES = 104

    def __init__(self):
        self._message_format = struct.Struct("<16sBI")
        self._registration_format = struct.Struct("255s160s")
        self._public_key_format = struct.Struct("16s")

        self._request_types = {
            self.REQUEST_REGISTER: self._parse_registration_request,
            self.REQUEST_LIST_USERS: self._no_operation,
            self.REQUEST_PUBLIC_KEY: self._parse_public_key_request,
            self.REQUEST_SEND_MESSAGE: self._parse_sent_message,
            self.REQUEST_READ_MESSAGES: self._no_operation
        }

    def _parse_registration_request(self, payload):
        name, public_key = self._registration_format.unpack(payload)
        return {
            "name": name.strip(b"\x00").decode("utf-8"), # Remove null terminators
            "public_key": public_key
        }

    def _parse_public_key_request(self, payload):
        uid = self._public_key_format.unpack(payload)[0]
        return {
            "uid": uid
        }

    def _parse_sent_message(self, payload):
        header = payload[:self._message_format.size]
        payload = payload[self._message_format.size:]
        uid, message_type, size = self._message_format.unpack(header)

        return {
            "recipient": uid,
            "type": message_type,
            "size": size,
            "content": payload
        }

    def _no_operation(self, payload):
        return {}


class ProtocolV1(PayloadBuilderMixin, PayloadParserMixin):
    def __init__(self):
        self._version = 1
        self._request_header = struct.Struct("<16sBBL")
        self._response_header = struct.Struct("<BHL")

        PayloadBuilderMixin.__init__(self)
        PayloadParserMixin.__init__(self)

    @property
    def request_header_size(self):
        return self._request_header.size

    @property
    def response_header_size(self):
        return self._response_header.size

    def _validate_version(self, version):
        if version != self._version:
            raise ValueError("Protocol version mismatch")

    def _parse_payload(self, payload_type, payload):
        return self._request_types[payload_type](payload)

    def parse_request_header(self, blob):
        uid, version, op, size = self._request_header.unpack(blob)
        self._validate_version(version)
        return uid, op, size

    def parse_request_payload(self, op, blob):
        return self._parse_payload(op, blob)

    def _make_response_header(self, op, payload):
        return self._response_header.pack(self._version, op, len(payload))

    def make_response(self, op, data):
        payload = self._response_type[op](data)
        header = self._make_response_header(op, payload)
        return header + payload
