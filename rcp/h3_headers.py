H3_FORBIDDEN_HEADERS = {
    b"connection",
    b"keep-alive",
    b"proxy-connection",
    b"transfer-encoding",
    b"upgrade"
}

H3_REQUEST_PSEUDO_HEADERS = {
    b":method",
    b":scheme",
    b":path",
    b":authority",
}

H3_RESPONSE_PSEUDO_HEADERS = {
    b":status"
}

H3_EXTENSION_PSEUDO_HEADERS = {
    b":protocol"
}