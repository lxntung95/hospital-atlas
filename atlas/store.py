"""Tables (T#): result sets stay server-side; the model only sees a handle and a small preview."""

from dataclasses import dataclass, field


@dataclass
class Table:
    id: str
    title: str
    columns: list[str]
    rows: list[dict]
    source_id: str | None = None
    meta: dict = field(default_factory=dict)

    def preview(self, n: int = 5) -> list[dict]:
        return self.rows[:n]


class TableStore:
    def __init__(self):
        self._tables: dict[str, Table] = {}

    def add(self, title: str, rows: list[dict], columns: list[str] | None = None, source_id: str | None = None, **meta) -> Table:
        cols = columns or (list(rows[0]) if rows else [])
        table = Table(f"T{len(self._tables) + 1}", title, cols, rows, source_id, meta)
        self._tables[table.id] = table
        return table

    def put(self, table_id: str, title: str, rows: list[dict], columns: list[str] | None = None, source_id: str | None = None, **meta) -> Table:
        """Add or replace a table under a fixed id (derived tables such as T_rank are recomputed on every analysis)."""
        table = Table(table_id, title, columns or (list(rows[0]) if rows else []), rows, source_id, meta)
        self._tables[table_id] = table
        return table

    def get(self, table_id: str) -> Table:
        if table_id not in self._tables:
            raise KeyError(f"unknown table {table_id}; known: {', '.join(self._tables) or 'none'}")
        return self._tables[table_id]

    def all(self) -> list[Table]:
        return list(self._tables.values())
