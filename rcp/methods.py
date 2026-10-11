from enum import Enum

class RequestMethod(Enum):
    GET = b"GET"
    POST = b"POST"
    PUT = b"PUT"
    PATCH = b"PATCH"
    DELETE = b"DELETE"
    HEAD = b"HEAD"
    OPTIONS = b"OPTIONS"
    TRACE = b"TRACE"
    CONNECT = b"CONNECT"