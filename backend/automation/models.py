from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, model_validator


class RestAuth(BaseModel):
    type: Literal["none", "api_key", "basic", "bearer"] = "none"
    header_name: str | None = None   # api_key: header to set (e.g. "X-API-Key")
    value_ref: str | None = None     # api_key/bearer: env var NAME holding the secret
    user_ref: str | None = None      # basic: env var name for username
    pass_ref: str | None = None      # basic: env var name for password


class Pagination(BaseModel):
    param: str = "page"
    start: int = 1


class RestSource(BaseModel):
    source_type: Literal["rest"] = "rest"
    url: str
    method: Literal["GET"] = "GET"
    headers: dict[str, str] = Field(default_factory=dict)   # values may contain ${VAR}
    params: dict[str, str] = Field(default_factory=dict)
    auth: RestAuth = Field(default_factory=RestAuth)
    records_path: str = ""           # dotted path to the array, e.g. "data.items"
    pagination: Pagination | None = None
    timeout_seconds: int = 30
    max_retries: int = 3


class SalesforceSource(BaseModel):
    source_type: Literal["salesforce"] = "salesforce"
    soql: str                                     # full SOQL query
    object_name: str                              # e.g. "Transaction__c" (for bulk2 routing)
    use_bulk: bool = True                         # True = bulk2 API (large tables), False = REST query_all
    user_ref: str = "SF_User"                     # env var name for username
    pass_ref: str = "SF_Password"                 # env var name for password
    token_ref: str = ""                           # env var name for security token ("" = no token)
    instance_url: str = "https://your-org.my.salesforce.com"


AnySource = Annotated[
    Union[RestSource, SalesforceSource],
    Field(discriminator="source_type"),
]


class ExportSpec(BaseModel):
    formats: list[Literal["duckdb", "parquet", "csv", "xlsx"]] = Field(default_factory=list)
    dest_dir: str
    duckdb_mode: Literal["overwrite", "append"] = "overwrite"
    xlsx_row_guard: int = 1_000_000


class EmailSpec(BaseModel):
    enabled: bool = False
    recipients: list[str] = Field(default_factory=list)
    attach_max_bytes: int = 10_485_760   # 10 MB


class NotifySpec(BaseModel):
    discord_enabled: bool = False
    email: EmailSpec = Field(default_factory=EmailSpec)


class JobConfig(BaseModel):
    name: str
    source: AnySource
    shape_sql: str = ""              # DuckDB SQL over `raw`; "" = passthrough
    export: ExportSpec
    notify: NotifySpec = Field(default_factory=NotifySpec)

    @model_validator(mode="before")
    @classmethod
    def _backfill_source_type(cls, data):
        """Old REST jobs stored before source_type was added lack the field — default to 'rest'."""
        if isinstance(data, dict) and isinstance(data.get("source"), dict):
            data["source"].setdefault("source_type", "rest")
        return data


class RunResult(BaseModel):
    status: Literal["ok", "warning", "error", "running"]
    rows: int = 0
    duration_seconds: float = 0.0
    output_files: list[str] = Field(default_factory=list)
    error: str | None = None


class AutomationJob(BaseModel):
    id: str
    config: JobConfig
    last_status: str | None = None
    last_run_at: str | None = None
    last_rows: int | None = None
    last_error: str | None = None
    created: str
    updated: str
