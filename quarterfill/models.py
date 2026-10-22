from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
import hashlib
import json


def stable_id(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]


@dataclass(frozen=True)
class Fact:
    cik: str
    concept: str
    label: str
    value: Decimal
    unit: str
    start: str | None
    end: str
    accession: str
    form: str
    filed: str
    url: str = ""
    section: str = ""
    context: str = ""
    dimensions: tuple = ()
    verified: bool = False
    decimals: str = "0"

    @property
    def id(self):
        return stable_id(asdict(self))


@dataclass
class Cell:
    company: str
    ticker: str
    metric: str
    year: int
    quarter: str
    start: str | None
    end: str | None
    status: str
    value: Decimal | None = None
    unit: str = ""
    inputs: list[Fact] = field(default_factory=list)
    operation: str = ""
    reasoning: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    investigation: list[dict] = field(default_factory=list)

    @property
    def verified(self):
        return self.value is not None and bool(self.inputs) and all(f.verified for f in self.inputs)

    @property
    def id(self):
        return stable_id([self.ticker, self.metric, self.year, self.quarter, self.start,
                          self.end, self.status, self.operation, [f.id for f in self.inputs]])

    @property
    def formula(self):
        if self.value is None:
            return ""
        values = [str(f.value) for f in self.inputs]
        return (f" {self.operation} ".join(values) if self.operation else values[0]) + f" = {self.value} {self.unit}"

    def audit(self):
        payload = asdict(self)
        payload.update(id=self.id, verified=self.verified, formula=self.formula,
                       confidence="Document matched" if self.verified else "Unverified / review required",
                       input_ids=[f.id for f in self.inputs])
        return json.loads(json.dumps(payload, default=str))
