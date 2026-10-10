"""Carga el contrato vigente de spec/ y reconstruye el copiado en cada lote (R1.5)."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from backend.app.contract.loader import (
    Contract, Master, contract_hash, parse_contract, parse_master,
)

SPEC_DIR = Path(__file__).resolve().parents[3] / "spec"


@dataclass(frozen=True)
class Bundle:
    contract: Contract
    master: Master
    contract_text: str
    master_text: str
    hash: str


@lru_cache(maxsize=16)
def bundle_from_texts(contract_text: str, master_text: str) -> Bundle:
    return Bundle(parse_contract(contract_text), parse_master(master_text), contract_text, master_text,
                  contract_hash(contract_text, master_text))


def current_bundle() -> Bundle:
    return bundle_from_texts(
        (SPEC_DIR / "timesheet_spec.yaml").read_text(encoding="utf-8"),
        (SPEC_DIR / "employee_master.csv").read_text(encoding="utf-8"),
    )
