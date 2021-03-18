import uuid
import sqlite3

import logger

class MessageUDatabase(object):
    _CREATE_USER_TABLE_SQL_CMD = """
        CREATE TABLE IF NOT EXISTS clients (
            id BINARY(16) PRIMARY KEY,
            name VARCHAR(255),
            public_key BINARY(160),
            last_seen TIMESTAMP
        )
    """

    _CREATE_MESSAGE_TABLE_SQL_CMD = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            recipient BINARY(16),
            sender BINARY(16),
            type INTEGER,
            content BLOB
        )
    """

    _SELECT_MESSAGES_SQL_CMD = """
        SELECT id, recipient, sender, content, type
        FROM messages
        WHERE recipient = ?
    """

    _DELETE_MESSAGES_SQL_CMD = """
        DELETE FROM messages
        WHERE recipient = ?
    """

    _INSERT_MESSAGE_SQL_CMD = """
        INSERT INTO messages (id, recipient, sender, type, content)
        VALUES(?, ?, ?, ?, ?)
    """

    _INSERT_USER_SQL_CMD = """
        INSERT INTO clients(id, name, public_key)
        VALUES(?, ?, ?)
    """

    _SELECT_USERS_SQL_CMD = """
        SELECT id, name
        FROM clients
        WHERE id != ?
    """

    _SELECT_PUBKEY_SQL_CMD = "SELECT public_key FROM clients WHERE id=?"

    def __init__(self, db_file=":memory:"):
        self._logger = logger.get_module_logger(__name__)
        self._logger.debug(f"DB connection to {db_file} now open")

        self._connection = sqlite3.connect(db_file)
        self._cursor = self._connection.cursor()

        self._cursor.execute(self._CREATE_USER_TABLE_SQL_CMD)
        self._cursor.execute(self._CREATE_MESSAGE_TABLE_SQL_CMD)

        self._message_counter = 0

    def _get_message_id(self):
        self._message_counter += 1
        return self._message_counter

    def register_user(self, name, pubkey):
        uid = uuid.uuid4().bytes
        self._cursor.execute(self._INSERT_USER_SQL_CMD, (uid, name, pubkey))
        return uid

    def get_users(self, exclude=b""):
        data = self._cursor.execute(self._SELECT_USERS_SQL_CMD, (exclude,)).fetchall()
        return [{"uid": i[0], "name": i[1]} for i in data]

    def put_user_message(self, sender, recipient, msg_type, content):
        data = (self._get_message_id(), recipient, sender, msg_type, content)
        self._cursor.execute(self._INSERT_MESSAGE_SQL_CMD, data)

    def pop_user_messages(self, recipient):
        data = self._cursor.execute(self._SELECT_MESSAGES_SQL_CMD, (recipient,)).fetchall()
        if data is None:
            return []

        data = [{"id": i[0], "recipient": i[1], "sender": i[2], "content": i[3], "type": i[4]} for i in data]
        data.sort(key=lambda x: x["id"])

        self._cursor.execute(self._DELETE_MESSAGES_SQL_CMD, (recipient,))
        return data

    def get_user_public_key(self, uid):
        data = self._cursor.execute(self._SELECT_PUBKEY_SQL_CMD, (uid,)).fetchall()
        return {"uid": uid, "public_key": data[0][0]}

    def close():
        self._logger.debug("Closing connection")
        self._cursor.close()
        self._connection.close()
