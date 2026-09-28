"""The config table (config/ConfigurationFile.csv): one row per setting.

    Table_Name, Class, Source, Parameter, Value
    DemoTable,  Landing Space, ADLS, Container_Name, aerodata-cont

Rows are grouped by table and then by source. The file is re-read on every
request, so edits show up on the next page load without a restart.
"""

import csv
import io
from dataclasses import dataclass, field

from . import settings
from .sources import SOURCES_BY_NAME

COLUMNS = ("Table_Name", "Class", "Source", "Parameter", "Value")


class ConfigError(Exception):
    pass


@dataclass
class TableConfig:
    name: str
    sources: dict = field(default_factory=dict)  # source key -> {parameter: value}
    rows: list = field(default_factory=list)     # the table's rows as written in the file


def _read_text(path):
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")  # Excel's "CSV UTF-8" starts the file with a byte-order mark
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp1252")  # Excel's default "CSV (Comma delimited)" on Windows
    except UnicodeDecodeError:
        raise ConfigError(f"{path.name} is not readable text. In Excel, save it as 'CSV UTF-8'.")


def load_config_table(path=None):
    """Return {table name: TableConfig}, in file order. Raises ConfigError on a bad row."""
    path = path or settings.CONFIG_TABLE_FILE
    if not path.exists():
        raise ConfigError(f"Config table not found: {path}")
    try:
        return _parse(csv.DictReader(io.StringIO(_read_text(path), newline="")), path.name)
    except csv.Error as exc:
        raise ConfigError(f"{path.name} is not a valid CSV file: {exc}")


def _parse(reader, file_name):
    tables = {}
    headers = {(name or "").strip().lower(): name for name in reader.fieldnames or []}
    missing = [name for name in COLUMNS if name.lower() not in headers]
    if missing:
        raise ConfigError(f"{file_name} is missing column(s): {', '.join(missing)}. "
                          f"Expected: {', '.join(COLUMNS)}")

    for line, row in enumerate(reader, start=2):
        values = {name: (row.get(headers[name.lower()]) or "").strip() for name in COLUMNS}
        if not any(values.values()):
            continue
        where = f"{file_name} line {line}"
        if not values["Table_Name"]:
            raise ConfigError(f"{where}: Table_Name is empty")
        if "/" in values["Table_Name"]:
            raise ConfigError(f"{where}: Table_Name can't contain '/' (it is part of the page address)")

        source = SOURCES_BY_NAME.get(values["Source"].lower())
        if not source:
            names = ", ".join(sorted({s.name for s in SOURCES_BY_NAME.values()}))
            raise ConfigError(f"{where}: unknown Source '{values['Source']}'. Use one of: {names}")
        if values["Class"].lower() != source.class_name.lower():
            raise ConfigError(f"{where}: {source.name} belongs to class '{source.class_name}', "
                              f"not '{values['Class']}'")
        parameter = next((p for p in source.parameters if p.lower() == values["Parameter"].lower()), None)
        if not parameter:
            raise ConfigError(f"{where}: unknown Parameter '{values['Parameter']}' for {source.name}. "
                              f"Use one of: {', '.join(source.parameters)}")

        table = tables.setdefault(values["Table_Name"], TableConfig(values["Table_Name"]))
        params = table.sources.setdefault(source.key, {})
        if parameter in params:
            raise ConfigError(f"{where}: {source.name} {parameter} is set twice for {table.name}")
        params[parameter] = values["Value"]
        table.rows.append({"class": source.class_name, "source": source.name,
                           "parameter": parameter, "value": values["Value"]})
    return tables
