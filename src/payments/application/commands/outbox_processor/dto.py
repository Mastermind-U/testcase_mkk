from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OutboxProcessorResult:
    fetched: int
    published: int
    retried: int
    dead_lettered: int
    deleted_old: int

    def is_not_mpty(self) -> bool:
        return any(
            (
                self.fetched,
                self.published,
                self.retried,
                self.dead_lettered,
                self.deleted_old,
            ),
        )
