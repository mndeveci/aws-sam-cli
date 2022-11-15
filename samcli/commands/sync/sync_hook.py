from dataclasses import dataclass
from enum import Enum


class SyncHookType(Enum):
    Infra = "Infra"
    Code = "Code"


@dataclass
class SyncHook:
    type: SyncHookType
    logical_id: str
    action: str
