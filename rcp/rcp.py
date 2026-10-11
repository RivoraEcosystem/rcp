from enum import StrEnum
from typing import TypedDict

class RCPVersions(StrEnum):
    VERSION_1 = "1.0"
    VERSION_2 = "2.0"

class RCP(TypedDict):
    version: RCPVersions