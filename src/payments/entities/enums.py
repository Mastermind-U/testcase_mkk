from enum import IntEnum


class OutboxStatus(IntEnum):
    PENDING = 1
    PUBLISHED = 2
    FAILED = 3
    DEAD_LETTER = 4
