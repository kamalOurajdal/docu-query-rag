from enum import Enum


class EmbeddingStatusEnum(Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
