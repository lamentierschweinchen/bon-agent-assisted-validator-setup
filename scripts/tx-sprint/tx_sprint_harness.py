#!/usr/bin/env python3

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import math
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from multiversx_sdk import (
    Address,
    AddressComputer,
    ProxyNetworkProvider,
    Transaction,
    TransactionComputer,
    TransactionsFactoryConfig,
    TransferTransactionsFactory,
    UserSigner,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_ROOT = Path(os.environ.get("TX_SPRINT_ROOT", REPO_ROOT / "artifacts" / "tx-sprint")).expanduser().resolve()
DEFAULT_CHAIN_ID = os.environ.get("TX_SPRINT_CHAIN_ID", "B")
DEFAULT_GATEWAY = os.environ.get("TX_SPRINT_GATEWAY", "https://gateway.battleofnodes.com")
DEFAULT_API = os.environ.get("TX_SPRINT_API", "https://api.battleofnodes.com")
DEFAULT_MXPY = Path(
    os.environ.get("TX_SPRINT_MXPY", "~/.local/pipx/venvs/multiversx-sdk-cli/bin/mxpy")
).expanduser().resolve()
MOVE_GAS_LIMIT = 50_000
MOVE_VALUE_ATOMIC = 1
MIN_GAS_PRICE = 1_000_000_000
DEFAULT_RECEIVER_MODE = "same-shard-ring"
SHARD_COMPUTER = AddressComputer(3)
NETWORK_RETRY_SECONDS = 120
NETWORK_RETRY_SLEEP_SECONDS = 2.0


@dataclass
class WalletEntry:
    index: int
    name: str
    pem: Path
    address: str
    shard: int
    default_receiver_address: str
    default_receiver_shard: int
    default_receiver_index: int

    def to_dict(self, base_dir: Path) -> dict[str, object]:
        return {
            "index": self.index,
            "name": self.name,
            "pem": os.path.relpath(self.pem, base_dir),
            "address": self.address,
            "shard": self.shard,
            "defaultReceiverAddress": self.default_receiver_address,
            "defaultReceiverShard": self.default_receiver_shard,
            "defaultReceiverIndex": self.default_receiver_index,
        }


@dataclass
class FundingEntry:
    wallet: WalletEntry
    amount_atomic: int
    current_balance_atomic: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "index": self.wallet.index,
            "name": self.wallet.name,
            "address": self.wallet.address,
            "shard": self.wallet.shard,
            "amountAtomic": self.amount_atomic,
            "amountEgld": egld_from_atomic(self.amount_atomic),
        }
        if self.current_balance_atomic is not None:
            payload["currentBalanceAtomic"] = self.current_balance_atomic
            payload["currentBalanceEgld"] = egld_from_atomic(self.current_balance_atomic)
        return payload


@dataclass
class SenderState:
    wallet: WalletEntry
    signer: UserSigner
    address_obj: Address
    next_nonce: int
    spendable_atomic: int
    outstanding_submissions: int = 0
    planned_count: int = 0
    accepted_count: int = 0
    blocked: bool = False
    blocked_reason: str = ""
    last_planned_nonce: int | None = None


@dataclass
class PreparedTx:
    sender_address: str
    receiver_address: str
    sender_shard: int
    receiver_shard: int
    nonce: int
    value_atomic: int
    gas_price: int
    gas_limit: int
    planned_fee_atomic: int
    predicted_hash: str
    transaction_dict: dict[str, object]
    transaction: Transaction


@dataclass
class BatchEnvelope:
    batch_id: int
    planned_at: str
    batch_file: Path
    response_file: Path
    records: list[PreparedTx]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_work_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    return resolved


def ensure_dir(path: Path) -> Path:
    resolved = ensure_work_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def atomic_write_text(path: Path, text: str) -> None:
    resolved = ensure_work_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temp_path = resolved.with_suffix(resolved.suffix + ".tmp")
    temp_path.write_text(text)
    temp_path.replace(resolved)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def append_ndjson(path: Path, payload: Any) -> None:
    resolved = ensure_work_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def parse_iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_shard_csv(value: str) -> tuple[int, ...]:
    shards: list[int] = []
    for piece in value.split(","):
        piece = piece.strip()
        if not piece:
            continue
        shard = int(piece)
        if shard not in (0, 1, 2):
            raise argparse.ArgumentTypeError("shards must only contain 0,1,2")
        if shard not in shards:
            shards.append(shard)
    if not shards:
        raise argparse.ArgumentTypeError("at least one shard is required")
    return tuple(shards)


def parse_float_csv(value: str) -> tuple[float, ...]:
    items = []
    for piece in value.split(","):
        piece = piece.strip()
        if not piece:
            continue
        items.append(float(piece))
    if not items:
        raise argparse.ArgumentTypeError("at least one value is required")
    return tuple(items)


def parse_int_csv(value: str) -> tuple[int, ...]:
    items = []
    for piece in value.split(","):
        piece = piece.strip()
        if not piece:
            continue
        items.append(int(piece))
    if not items:
        raise argparse.ArgumentTypeError("at least one value is required")
    return tuple(items)


def require_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"missing file: {resolved}")
    return resolved


def atomic_from_egld(amount: str) -> int:
    whole, dot, frac = amount.partition(".")
    frac = (frac + "0" * 18)[:18]
    return int(whole or "0") * 10**18 + int(frac)


def egld_from_atomic(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    whole = absolute // 10**18
    frac = absolute % 10**18
    if frac == 0:
        return f"{sign}{whole}"
    frac_text = f"{frac:018d}".rstrip("0")
    return f"{sign}{whole}.{frac_text}"


def per_tx_cost_atomic(gas_price: int, value_atomic: int) -> int:
    return MOVE_GAS_LIMIT * gas_price + value_atomic


def planned_fee_atomic(gas_price: int) -> int:
    return MOVE_GAS_LIMIT * gas_price


def ensure_positive(label: str, value: int) -> int:
    if value <= 0:
        raise SystemExit(f"{label} must be positive")
    return value


def build_provider(proxy: str) -> ProxyNetworkProvider:
    return ProxyNetworkProvider(proxy)


def api_get_json(base_url: str, relative_path: str) -> Any:
    url = base_url.rstrip("/") + "/" + relative_path.lstrip("/")
    deadline = time.time() + NETWORK_RETRY_SECONDS
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            time.sleep(NETWORK_RETRY_SLEEP_SECONDS)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def unwrap_transaction_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        data = payload["data"]
        if "transaction" in data:
            return data["transaction"]
    return payload


def fetch_transaction_json(api_url: str, tx_hash: str) -> Any:
    safe_hash = urllib.parse.quote(tx_hash)
    payload = api_get_json(api_url, f"transactions/{safe_hash}?withResults=true")
    return unwrap_transaction_payload(payload)


def fetch_account_nonce_and_balance(proxy: str, address: str) -> tuple[int, int]:
    provider = build_provider(proxy)
    account = provider.get_account(Address.new_from_bech32(address))
    return account.nonce, int(account.balance)


def fetch_balances(proxy: str, addresses: Sequence[str], workers: int) -> dict[str, tuple[int, int]]:
    results: dict[str, tuple[int, int]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(fetch_account_nonce_and_balance, proxy, address): address for address in addresses
        }
        for future in concurrent.futures.as_completed(future_map):
            address = future_map[future]
            results[address] = future.result()
    return results


def shard_counts_for(total: int, shards: Sequence[int]) -> dict[int, int]:
    counts = {shard: 0 for shard in shards}
    base = total // len(shards)
    remainder = total % len(shards)
    for shard in shards:
        counts[shard] = base
    for shard in shards[:remainder]:
        counts[shard] += 1
    return counts


def signer_from_pem(path: Path) -> UserSigner:
    return UserSigner.from_pem_file(require_file(path))


def address_from_signer(signer: UserSigner) -> str:
    return signer.get_pubkey().to_address("erd").to_bech32()


def group_wallets_by_shard(wallets: Sequence[WalletEntry]) -> dict[int, list[WalletEntry]]:
    groups = {0: [], 1: [], 2: []}
    for wallet in wallets:
        groups[wallet.shard].append(wallet)
    return groups


def assign_default_receivers(wallets: Sequence[WalletEntry]) -> list[WalletEntry]:
    groups = group_wallets_by_shard(wallets)
    receiver_map: dict[str, WalletEntry] = {}
    for shard, shard_wallets in groups.items():
        if not shard_wallets:
            continue
        if len(shard_wallets) == 1:
            receiver_map[shard_wallets[0].address] = shard_wallets[0]
            continue
        for index, wallet in enumerate(shard_wallets):
            receiver_map[wallet.address] = shard_wallets[(index + 1) % len(shard_wallets)]

    assigned: list[WalletEntry] = []
    for wallet in wallets:
        receiver = receiver_map[wallet.address]
        assigned.append(
            WalletEntry(
                index=wallet.index,
                name=wallet.name,
                pem=wallet.pem,
                address=wallet.address,
                shard=wallet.shard,
                default_receiver_address=receiver.address,
                default_receiver_shard=receiver.shard,
                default_receiver_index=receiver.index,
            )
        )
    return assigned


def load_manifest(path: Path) -> tuple[dict[str, object], list[WalletEntry]]:
    resolved = require_file(path)
    payload = json.loads(resolved.read_text())
    base_dir = resolved.parent
    wallets = [
        WalletEntry(
            index=item["index"],
            name=item["name"],
            pem=(base_dir / item["pem"]).resolve(),
            address=item["address"],
            shard=item["shard"],
            default_receiver_address=item["defaultReceiverAddress"],
            default_receiver_shard=item["defaultReceiverShard"],
            default_receiver_index=item["defaultReceiverIndex"],
        )
        for item in payload["wallets"]
    ]
    return payload, wallets


def save_manifest(path: Path, metadata: dict[str, object], wallets: Sequence[WalletEntry]) -> None:
    resolved = ensure_work_path(path)
    payload = dict(metadata)
    payload["wallets"] = [wallet.to_dict(resolved.parent) for wallet in wallets]
    atomic_write_json(resolved, payload)


def wait_until(timestamp: str | None) -> None:
    if not timestamp:
        return
    target = parse_iso_utc(timestamp)
    while True:
        remaining = (target - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return
        sleep_for = min(remaining, 10)
        print(f"waiting until {target.isoformat()} ({remaining:.1f}s remaining)", flush=True)
        time.sleep(sleep_for)


def create_run_dir(parent: Path, label: str) -> Path:
    return ensure_dir(parent / f"{stamp_utc()}-{label}")


def filter_wallets(
    wallets: Sequence[WalletEntry],
    wallet_limit: int | None,
    sender_shards: Sequence[int] | None,
) -> list[WalletEntry]:
    filtered = list(wallets)
    if sender_shards:
        allowed = set(sender_shards)
        filtered = [wallet for wallet in filtered if wallet.shard in allowed]
    if wallet_limit is not None:
        filtered = filtered[:wallet_limit]
    if not filtered:
        raise SystemExit("no wallets matched the requested filters")
    return filtered


def network_defaults_metadata(gateway: str, api: str) -> dict[str, object]:
    return {
        "chainId": DEFAULT_CHAIN_ID,
        "gateway": gateway,
        "api": api,
        "minimumMoveValueAtomic": MOVE_VALUE_ATOMIC,
        "minimumGasPrice": MIN_GAS_PRICE,
        "moveGasLimit": MOVE_GAS_LIMIT,
        "defaultReceiverMode": DEFAULT_RECEIVER_MODE,
    }


def build_transfer_factory() -> TransferTransactionsFactory:
    return TransferTransactionsFactory(TransactionsFactoryConfig(chain_id=DEFAULT_CHAIN_ID))


def prepare_transfer(
    sender: SenderState,
    receiver: WalletEntry,
    value_atomic: int,
    gas_price: int,
    computer: TransactionComputer,
    factory: TransferTransactionsFactory,
) -> PreparedTx:
    tx = factory.create_transaction_for_native_token_transfer(
        sender=sender.address_obj,
        receiver=Address.new_from_bech32(receiver.address),
        native_amount=value_atomic,
    )
    tx.nonce = sender.next_nonce
    tx.gas_price = gas_price
    tx.gas_limit = MOVE_GAS_LIMIT
    tx.signature = sender.signer.sign(computer.compute_bytes_for_signing(tx))
    predicted_hash = computer.compute_transaction_hash(tx).hex()
    return PreparedTx(
        sender_address=sender.wallet.address,
        receiver_address=receiver.address,
        sender_shard=sender.wallet.shard,
        receiver_shard=receiver.shard,
        nonce=sender.next_nonce,
        value_atomic=value_atomic,
        gas_price=gas_price,
        gas_limit=MOVE_GAS_LIMIT,
        planned_fee_atomic=planned_fee_atomic(gas_price),
        predicted_hash=predicted_hash,
        transaction_dict=tx.to_dictionary(),
        transaction=tx,
    )


def choose_receiver(
    wallet: WalletEntry,
    mode: str,
    groups: dict[int, list[WalletEntry]],
    cross_shard_offsets: dict[str, int],
) -> WalletEntry:
    if mode == "same-shard-ring":
        return next(candidate for candidate in groups[wallet.shard] if candidate.address == wallet.default_receiver_address)
    if mode == "cross-shard-ring":
        candidate_shards = [shard for shard in (0, 1, 2) if shard != wallet.shard and groups[shard]]
        if not candidate_shards:
            raise SystemExit("cross-shard receiver mode requires wallets in at least two shards")
        offset = cross_shard_offsets.get(wallet.address, 0)
        destination_shard = candidate_shards[offset % len(candidate_shards)]
        receiver_group = groups[destination_shard]
        receiver = receiver_group[(offset // len(candidate_shards)) % len(receiver_group)]
        cross_shard_offsets[wallet.address] = offset + 1
        return receiver
    raise SystemExit(f"unsupported receiver mode: {mode}")


def planned_batch_payload(batch: BatchEnvelope, dry_run: bool) -> dict[str, object]:
    return {
        "batchId": batch.batch_id,
        "plannedAt": batch.planned_at,
        "txCount": len(batch.records),
        "dryRun": dry_run,
        "transactions": [
            {
                "sender": record.sender_address,
                "receiver": record.receiver_address,
                "senderShard": record.sender_shard,
                "receiverShard": record.receiver_shard,
                "nonce": record.nonce,
                "valueAtomic": record.value_atomic,
                "gasPrice": record.gas_price,
                "gasLimit": record.gas_limit,
                "plannedFeeAtomic": record.planned_fee_atomic,
                "predictedHash": record.predicted_hash,
                "transaction": record.transaction_dict,
            }
            for record in batch.records
        ],
    }


def submit_batch(proxy: str, batch: BatchEnvelope, dry_run: bool) -> dict[str, object]:
    if dry_run:
        response = {
            "batchId": batch.batch_id,
            "submittedAt": now_utc(),
            "accepted": len(batch.records),
            "returnedHashes": [record.predicted_hash for record in batch.records],
            "dryRun": True,
        }
        atomic_write_json(batch.response_file, response)
        return response

    provider = build_provider(proxy)
    started_at = now_utc()
    try:
        accepted, hashes = provider.send_transactions([record.transaction for record in batch.records])
        returned_hashes = [item.hex() for item in hashes]
        response = {
            "batchId": batch.batch_id,
            "submittedAt": started_at,
            "completedAt": now_utc(),
            "accepted": accepted,
            "returnedHashes": returned_hashes,
            "error": None,
        }
    except Exception as error:  # pragma: no cover - network-facing path
        response = {
            "batchId": batch.batch_id,
            "submittedAt": started_at,
            "completedAt": now_utc(),
            "accepted": 0,
            "returnedHashes": [],
            "error": {
                "type": error.__class__.__name__,
                "message": str(error),
            },
        }
    atomic_write_json(batch.response_file, response)
    return response


def count_nonempty_hashes(returned_hashes: Sequence[object]) -> int:
    return len([item for item in returned_hashes if str(item or "").strip()])


def wait_for_account_nonce(
    proxy: str,
    address: str,
    target_nonce: int,
    timeout_seconds: int,
    poll_seconds: float,
) -> tuple[int, int]:
    deadline = time.time() + timeout_seconds
    last_nonce = -1
    last_balance = 0
    while time.time() <= deadline:
        last_nonce, last_balance = fetch_account_nonce_and_balance(proxy, address)
        if last_nonce >= target_nonce:
            return last_nonce, last_balance
        time.sleep(poll_seconds)
    raise RuntimeError(f"account {address} did not reach nonce {target_nonce} before timeout; last nonce {last_nonce}")


def update_run_summary(summary_path: Path, summary: dict[str, object]) -> None:
    summary["updatedAt"] = now_utc()
    atomic_write_json(summary_path, summary)


def mark_blocked_senders(
    run_dir: Path,
    senders: Iterable[SenderState],
    reason: str,
) -> None:
    blocked = []
    for sender in senders:
        sender.blocked = True
        sender.blocked_reason = reason
        blocked.append(
            {
                "address": sender.wallet.address,
                "name": sender.wallet.name,
                "shard": sender.wallet.shard,
                "lastPlannedNonce": sender.last_planned_nonce,
                "nextNonceHint": sender.next_nonce,
                "reason": reason,
            }
        )
    if blocked:
        append_ndjson(run_dir / "blocked-senders.ndjson", {"recordedAt": now_utc(), "blocked": blocked})


def execute_sender_run(
    *,
    manifest_path: Path,
    wallets: Sequence[WalletEntry],
    label: str,
    gateway: str,
    api: str,
    receiver_mode: str,
    tx_value_atomic: int,
    gas_price: int,
    batch_size: int,
    num_workers: int,
    inflight_nonces_per_sender: int,
    duration_seconds: int | None,
    stop_at: str | None,
    stop_seconds_early: int,
    budget_atomic: int | None,
    halt_on_ambiguous_batch: bool,
    dry_run: bool,
    run_parent: Path,
    run_kind: str,
) -> Path:
    ensure_positive("batch_size", batch_size)
    ensure_positive("num_workers", num_workers)
    ensure_positive("inflight_nonces_per_sender", inflight_nonces_per_sender)
    ensure_positive("gas_price", gas_price)
    ensure_positive("tx_value_atomic", tx_value_atomic)

    start_wait_target = None
    if stop_at and duration_seconds:
        raise SystemExit("use either duration_seconds or stop_at, not both")
    if stop_at:
        hard_stop = parse_iso_utc(stop_at)
    else:
        if duration_seconds is None:
            raise SystemExit("duration_seconds is required when stop_at is not provided")
        hard_stop = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

    effective_stop_early = stop_seconds_early
    if duration_seconds is not None:
        effective_stop_early = min(stop_seconds_early, max(0, duration_seconds - 1))

    planner_stop = hard_stop - timedelta(seconds=effective_stop_early)
    if planner_stop <= datetime.now(timezone.utc):
        raise SystemExit("planner stop time is already in the past")

    run_dir = create_run_dir(run_parent, label)
    batches_dir = ensure_dir(run_dir / "batches")
    summary_path = run_dir / "run.json"
    atomic_write_json(run_dir / "manifest-copy.json", json.loads(require_file(manifest_path).read_text()))

    addresses = [wallet.address for wallet in wallets]
    if dry_run:
        synthetic_balance = budget_atomic if budget_atomic is not None else 10**24
        balances = {address: (0, synthetic_balance) for address in addresses}
    else:
        balances = fetch_balances(gateway, addresses, min(32, max(4, len(wallets))))
    signers = {wallet.address: signer_from_pem(wallet.pem) for wallet in wallets}
    sender_states = [
        SenderState(
            wallet=wallet,
            signer=signers[wallet.address],
            address_obj=Address.new_from_bech32(wallet.address),
            next_nonce=balances[wallet.address][0],
            spendable_atomic=balances[wallet.address][1],
        )
        for wallet in wallets
    ]
    sender_by_address = {sender.wallet.address: sender for sender in sender_states}
    grouped_wallets = group_wallets_by_shard(wallets)
    cross_shard_offsets: dict[str, int] = {}
    planner_cursor = 0
    total_planned = 0
    total_attempted = 0
    max_total_transactions = None
    if budget_atomic is not None:
        tx_fee_atomic = planned_fee_atomic(gas_price)
        max_total_transactions = budget_atomic // tx_fee_atomic

    summary: dict[str, object] = {
        "kind": run_kind,
        "createdAt": now_utc(),
        "completedAt": None,
        "manifest": str(manifest_path),
        "walletCount": len(wallets),
        "gateway": gateway,
        "api": api,
        "receiverMode": receiver_mode,
        "txValueAtomic": tx_value_atomic,
        "gasPrice": gas_price,
        "gasLimit": MOVE_GAS_LIMIT,
        "batchSize": batch_size,
        "numWorkers": num_workers,
        "inflightNoncesPerSender": inflight_nonces_per_sender,
        "durationSeconds": duration_seconds,
        "stopAt": hard_stop.isoformat().replace("+00:00", "Z"),
        "plannerStopAt": planner_stop.isoformat().replace("+00:00", "Z"),
        "stopSecondsEarlyRequested": stop_seconds_early,
        "stopSecondsEarlyEffective": effective_stop_early,
        "budgetAtomic": budget_atomic,
        "budgetEgld": egld_from_atomic(budget_atomic) if budget_atomic is not None else None,
        "maxTotalTransactionsByBudget": max_total_transactions,
        "dryRun": dry_run,
        "counts": {
            "batchesPlanned": 0,
            "batchesCompleted": 0,
            "batchesAmbiguous": 0,
            "batchesCleanAccepted": 0,
            "plannedTransactions": 0,
            "acceptedTransactions": 0,
            "ambiguousTransactions": 0,
            "blockedSenders": 0,
        },
        "submissionSpan": {
            "startedAt": None,
            "lastCompletedAt": None,
            "seconds": None,
        },
        "estimatedFeeAtomic": {
            "planned": 0,
            "accepted": 0,
        },
    }
    update_run_summary(summary_path, summary)

    computer = TransactionComputer()
    factory = build_transfer_factory()
    batch_sequence = 0
    pending: dict[concurrent.futures.Future[dict[str, object]], BatchEnvelope] = {}
    stop_planning = False

    def next_eligible_sender() -> SenderState | None:
        nonlocal planner_cursor
        tx_cost = per_tx_cost_atomic(gas_price, tx_value_atomic)
        for _ in range(len(sender_states)):
            sender = sender_states[planner_cursor]
            planner_cursor = (planner_cursor + 1) % len(sender_states)
            if sender.blocked:
                continue
            if sender.outstanding_submissions >= inflight_nonces_per_sender:
                continue
            if sender.spendable_atomic < tx_cost:
                continue
            return sender
        return None

    def has_eligible_sender() -> bool:
        tx_cost = per_tx_cost_atomic(gas_price, tx_value_atomic)
        for sender in sender_states:
            if sender.blocked:
                continue
            if sender.outstanding_submissions >= inflight_nonces_per_sender:
                continue
            if sender.spendable_atomic < tx_cost:
                continue
            return True
        return False

    def plan_one_batch() -> BatchEnvelope | None:
        nonlocal batch_sequence, total_planned
        records: list[PreparedTx] = []
        tx_cost = per_tx_cost_atomic(gas_price, tx_value_atomic)
        while len(records) < batch_size:
            if max_total_transactions is not None and total_planned >= max_total_transactions:
                break
            sender = next_eligible_sender()
            if sender is None:
                break
            receiver = choose_receiver(sender.wallet, receiver_mode, grouped_wallets, cross_shard_offsets)
            record = prepare_transfer(sender, receiver, tx_value_atomic, gas_price, computer, factory)
            sender.next_nonce += 1
            sender.outstanding_submissions += 1
            sender.planned_count += 1
            sender.last_planned_nonce = record.nonce
            sender.spendable_atomic -= tx_cost
            total_planned += 1
            records.append(record)
        if not records:
            return None
        batch_sequence += 1
        batch = BatchEnvelope(
            batch_id=batch_sequence,
            planned_at=now_utc(),
            batch_file=batches_dir / f"{batch_sequence:06d}-planned.json",
            response_file=batches_dir / f"{batch_sequence:06d}-response.json",
            records=records,
        )
        atomic_write_json(batch.batch_file, planned_batch_payload(batch, dry_run))
        return batch

    def handle_batch_result(batch: BatchEnvelope, response: dict[str, object]) -> None:
        counts = summary["counts"]
        counts["batchesCompleted"] += 1
        summary["submissionSpan"]["lastCompletedAt"] = response.get("completedAt", now_utc())
        if summary["submissionSpan"]["startedAt"] is None:
            summary["submissionSpan"]["startedAt"] = batch.planned_at

        senders_in_batch = []
        seen = set()
        for record in batch.records:
            sender = sender_by_address[record.sender_address]
            sender.outstanding_submissions = max(0, sender.outstanding_submissions - 1)
            if sender.wallet.address not in seen:
                senders_in_batch.append(sender)
                seen.add(sender.wallet.address)

        returned_hashes = response.get("returnedHashes", [])
        clean_accept = (
            response.get("error") is None
            and response.get("accepted") == len(batch.records)
            and len(returned_hashes) == len(batch.records)
            and all(record.predicted_hash == returned_hash for record, returned_hash in zip(batch.records, returned_hashes))
        )
        if clean_accept:
            counts["batchesCleanAccepted"] += 1
            counts["acceptedTransactions"] += len(batch.records)
            summary["estimatedFeeAtomic"]["accepted"] += sum(record.planned_fee_atomic for record in batch.records)
            for record, returned_hash in zip(batch.records, returned_hashes):
                sender = sender_by_address[record.sender_address]
                sender.accepted_count += 1
                append_ndjson(
                    run_dir / "txs.ndjson",
                    {
                        "recordedAt": now_utc(),
                        "batchId": batch.batch_id,
                        "submissionState": "accepted",
                        "sender": record.sender_address,
                        "receiver": record.receiver_address,
                        "senderShard": record.sender_shard,
                        "receiverShard": record.receiver_shard,
                        "nonce": record.nonce,
                        "valueAtomic": record.value_atomic,
                        "gasPrice": record.gas_price,
                        "gasLimit": record.gas_limit,
                        "plannedFeeAtomic": record.planned_fee_atomic,
                        "predictedHash": record.predicted_hash,
                        "gatewayHash": returned_hash,
                        "hashMatched": record.predicted_hash == returned_hash,
                    },
                )
            return

        counts["batchesAmbiguous"] += 1
        counts["ambiguousTransactions"] += len(batch.records)
        reason = "ambiguous batch response"
        if response.get("error"):
            reason = f"batch error: {response['error'].get('type')} {response['error'].get('message')}"
        mark_blocked_senders(run_dir, senders_in_batch, reason)
        counts["blockedSenders"] = len([sender for sender in sender_states if sender.blocked])
        for index, record in enumerate(batch.records):
            append_ndjson(
                run_dir / "txs.ndjson",
                {
                    "recordedAt": now_utc(),
                    "batchId": batch.batch_id,
                    "submissionState": "ambiguous",
                    "sender": record.sender_address,
                    "receiver": record.receiver_address,
                    "senderShard": record.sender_shard,
                    "receiverShard": record.receiver_shard,
                    "nonce": record.nonce,
                    "valueAtomic": record.value_atomic,
                    "gasPrice": record.gas_price,
                    "gasLimit": record.gas_limit,
                    "plannedFeeAtomic": record.planned_fee_atomic,
                    "predictedHash": record.predicted_hash,
                    "gatewayHash": returned_hashes[index] if index < len(returned_hashes) else None,
                    "batchResponse": response,
                },
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        while True:
            now = datetime.now(timezone.utc)
            planning_open = not stop_planning and now < planner_stop
            while planning_open and len(pending) < num_workers:
                batch = plan_one_batch()
                if batch is None:
                    break
                summary["counts"]["batchesPlanned"] += 1
                summary["counts"]["plannedTransactions"] += len(batch.records)
                summary["estimatedFeeAtomic"]["planned"] += sum(record.planned_fee_atomic for record in batch.records)
                summary["counts"]["blockedSenders"] = len([sender for sender in sender_states if sender.blocked])
                update_run_summary(summary_path, summary)
                future = executor.submit(submit_batch, gateway, batch, dry_run)
                pending[future] = batch
                total_attempted += len(batch.records)
                if max_total_transactions is not None and total_planned >= max_total_transactions:
                    stop_planning = True
                    planning_open = False
                    break
            if not pending:
                if not planning_open:
                    break
                if not has_eligible_sender():
                    break
                continue

            done, _ = concurrent.futures.wait(
                pending.keys(),
                timeout=0.25,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if not done:
                if datetime.now(timezone.utc) >= planner_stop:
                    stop_planning = True
                continue
            for future in done:
                batch = pending.pop(future)
                response = future.result()
                handle_batch_result(batch, response)
                if halt_on_ambiguous_batch and summary["counts"]["batchesAmbiguous"] > 0:
                    stop_planning = True
                update_run_summary(summary_path, summary)
            if datetime.now(timezone.utc) >= planner_stop:
                stop_planning = True

    span_start = summary["submissionSpan"]["startedAt"]
    span_end = summary["submissionSpan"]["lastCompletedAt"]
    if span_start and span_end:
        seconds = max(0.0, (parse_iso_utc(span_end) - parse_iso_utc(span_start)).total_seconds())
        summary["submissionSpan"]["seconds"] = seconds

    summary["completedAt"] = now_utc()
    update_run_summary(summary_path, summary)

    sender_summary = [
        {
            "address": sender.wallet.address,
            "name": sender.wallet.name,
            "shard": sender.wallet.shard,
            "nextNonceHint": sender.next_nonce,
            "plannedCount": sender.planned_count,
            "acceptedCount": sender.accepted_count,
            "blocked": sender.blocked,
            "blockedReason": sender.blocked_reason,
            "remainingSpendableAtomic": sender.spendable_atomic,
            "remainingSpendableEgld": egld_from_atomic(sender.spendable_atomic),
        }
        for sender in sender_states
    ]
    atomic_write_json(run_dir / "senders-summary.json", sender_summary)
    return run_dir


def classify_transaction_status(tx: dict[str, object]) -> str:
    status = str(tx.get("status", "unknown")).lower()
    if status == "success":
        return "success"
    if status in {"fail", "failed", "invalid"}:
        return "failed"
    if status in {"pending", "received", "executed"}:
        return "pending"
    return "unknown"


def read_tx_records(run_dir: Path) -> list[dict[str, object]]:
    txs_path = ensure_work_path(run_dir / "txs.ndjson")
    if not txs_path.exists():
        return []
    records = []
    for line in txs_path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def fetch_transaction_detail(api: str, tx_hash: str) -> tuple[str, dict[str, object] | None]:
    try:
        payload = fetch_transaction_json(api, tx_hash)
        if isinstance(payload, dict) and payload.get("txHash"):
            return "found", payload
        return "unknown", payload if isinstance(payload, dict) else None
    except Exception as error:  # pragma: no cover - network-facing path
        text = str(error)
        lowered = text.lower()
        if "404" in lowered or "not found" in lowered:
            return "not_found", None
        return "error", {"error": text}


def report_run(
    run_dir: Path,
    api: str,
    workers: int,
    sample_size: int,
) -> dict[str, object]:
    summary = json.loads(ensure_work_path(run_dir / "run.json").read_text())
    tx_records = read_tx_records(run_dir)
    hash_map: dict[str, dict[str, object]] = {}
    for record in tx_records:
        if record.get("submissionState") == "notAccepted":
            continue
        chosen_hash = record.get("gatewayHash") or record.get("predictedHash")
        if not chosen_hash:
            continue
        hash_map[str(chosen_hash)] = record

    counts = {
        "accepted": len([record for record in tx_records if record.get("submissionState") == "accepted"]),
        "notAccepted": len([record for record in tx_records if record.get("submissionState") == "notAccepted"]),
        "ambiguous": len([record for record in tx_records if record.get("submissionState") == "ambiguous"]),
        "success": 0,
        "failed": 0,
        "pending": 0,
        "notFound": 0,
        "unknown": 0,
    }
    fee_atomic = {
        "estimatedAccepted": sum(int(record["plannedFeeAtomic"]) for record in tx_records if record.get("submissionState") == "accepted"),
        "observedAllFound": 0,
        "observedSuccessOnly": 0,
    }
    detail_samples: list[dict[str, object]] = []
    transaction_details_path = run_dir / "status-cache.ndjson"
    if transaction_details_path.exists():
        transaction_details_path.unlink()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(fetch_transaction_detail, api, tx_hash): tx_hash for tx_hash in hash_map
        }
        for future in concurrent.futures.as_completed(future_map):
            tx_hash = future_map[future]
            fetch_state, tx_detail = future.result()
            record = hash_map[tx_hash]
            entry = {
                "recordedAt": now_utc(),
                "hash": tx_hash,
                "submissionState": record.get("submissionState"),
                "fetchState": fetch_state,
                "sender": record.get("sender"),
                "receiver": record.get("receiver"),
                "nonce": record.get("nonce"),
            }
            if tx_detail:
                entry["tx"] = tx_detail
            append_ndjson(transaction_details_path, entry)

            if fetch_state == "found" and tx_detail:
                bucket = classify_transaction_status(tx_detail)
                counts[bucket] += 1
                fee_value = int(str(tx_detail.get("fee", "0")))
                fee_atomic["observedAllFound"] += fee_value
                if bucket == "success":
                    fee_atomic["observedSuccessOnly"] += fee_value
                if bucket != "success" and len(detail_samples) < sample_size:
                    detail_samples.append(
                        {
                            "hash": tx_hash,
                            "bucket": bucket,
                            "status": tx_detail.get("status"),
                            "sender": tx_detail.get("sender"),
                            "receiver": tx_detail.get("receiver"),
                            "nonce": tx_detail.get("nonce"),
                        }
                    )
                continue
            if fetch_state == "not_found":
                counts["notFound"] += 1
            else:
                counts["unknown"] += 1
            if len(detail_samples) < sample_size:
                detail_samples.append({"hash": tx_hash, "bucket": fetch_state, "submissionState": record.get("submissionState")})

    span_seconds = summary.get("submissionSpan", {}).get("seconds") or 0
    accepted_tps = counts["accepted"] / span_seconds if span_seconds else None
    confirmed_tps = counts["success"] / span_seconds if span_seconds else None
    report = {
        "reportedAt": now_utc(),
        "runDir": str(run_dir),
        "kind": summary.get("kind"),
        "walletCount": summary.get("walletCount"),
        "receiverMode": summary.get("receiverMode"),
        "gasPrice": summary.get("gasPrice"),
        "batchSize": summary.get("batchSize"),
        "numWorkers": summary.get("numWorkers"),
        "inflightNoncesPerSender": summary.get("inflightNoncesPerSender"),
        "counts": counts,
        "feeAtomic": fee_atomic,
        "feeEgld": {
            "estimatedAccepted": egld_from_atomic(fee_atomic["estimatedAccepted"]),
            "observedAllFound": egld_from_atomic(fee_atomic["observedAllFound"]),
            "observedSuccessOnly": egld_from_atomic(fee_atomic["observedSuccessOnly"]),
        },
        "submissionSpanSeconds": span_seconds,
        "rates": {
            "acceptedTxPerSec": accepted_tps,
            "confirmedTxPerSec": confirmed_tps,
        },
        "nonSuccessSamples": detail_samples,
    }
    atomic_write_json(run_dir / "report.json", report)
    return report


def command_generate_wallets(args: argparse.Namespace) -> None:
    output_dir = ensure_work_path(args.output_dir.resolve())
    wallets_dir = ensure_dir(output_dir / "wallets")
    manifest_path = output_dir / "manifest.json"
    mxpy = require_file(args.mxpy)
    shard_counts = shard_counts_for(args.count, args.shards if args.layout == "balanced" else (args.shard,))

    created: list[WalletEntry] = []
    global_index = 0
    for shard, count in shard_counts.items():
        for shard_index in range(count):
            name = f"{args.prefix}-s{shard}-{shard_index + 1:03d}"
            pem_path = wallets_dir / f"{name}.pem"
            if pem_path.exists() and not args.overwrite:
                raise SystemExit(f"{pem_path} already exists; use --overwrite or another directory")
            subprocess.run(
                [
                    str(mxpy),
                    "wallet",
                    "new",
                    "--format",
                    "pem",
                    "--outfile",
                    str(pem_path),
                    "--shard",
                    str(shard),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            signer = signer_from_pem(pem_path)
            address = address_from_signer(signer)
            actual_shard = SHARD_COMPUTER.get_shard_of_address(Address.new_from_bech32(address))
            created.append(
                WalletEntry(
                    index=global_index,
                    name=name,
                    pem=pem_path,
                    address=address,
                    shard=actual_shard,
                    default_receiver_address=address,
                    default_receiver_shard=actual_shard,
                    default_receiver_index=global_index,
                )
            )
            global_index += 1

    assigned = assign_default_receivers(created)
    metadata = {
        "createdAt": now_utc(),
        "count": len(assigned),
        "layout": args.layout,
        "requestedShards": list(args.shards if args.layout == "balanced" else (args.shard,)),
        "walletPrefix": args.prefix,
        **network_defaults_metadata(args.gateway, args.api),
        "shardCounts": {
            str(shard): len([wallet for wallet in assigned if wallet.shard == shard]) for shard in (0, 1, 2)
        },
    }
    save_manifest(manifest_path, metadata, assigned)
    print(f"generated {len(assigned)} wallets")
    print(f"manifest: {manifest_path}")


def build_funding_plan(
    *,
    manifest_path: Path,
    wallets: Sequence[WalletEntry],
    gateway: str,
    per_wallet_atomic: int | None,
    target_balance_atomic: int | None,
) -> list[FundingEntry]:
    if (per_wallet_atomic is None) == (target_balance_atomic is None):
        raise SystemExit("provide exactly one of per_wallet_atomic or target_balance_atomic")
    if per_wallet_atomic is not None:
        return [FundingEntry(wallet=wallet, amount_atomic=per_wallet_atomic) for wallet in wallets]

    balances = fetch_balances(gateway, [wallet.address for wallet in wallets], min(32, max(4, len(wallets))))
    entries = []
    for wallet in wallets:
        _, balance = balances[wallet.address]
        needed = max(0, target_balance_atomic - balance)
        if needed == 0:
            continue
        entries.append(FundingEntry(wallet=wallet, amount_atomic=needed, current_balance_atomic=balance))
    return entries


def command_plan_funding(args: argparse.Namespace) -> None:
    manifest_meta, wallets = load_manifest(args.manifest.resolve())
    selected = filter_wallets(wallets, args.wallet_limit, args.sender_shards)
    per_wallet_atomic = args.amount_atomic or (atomic_from_egld(args.amount_egld) if args.amount_egld else None)
    target_balance_atomic = args.target_balance_atomic or (
        atomic_from_egld(args.target_balance_egld) if args.target_balance_egld else None
    )
    entries = build_funding_plan(
        manifest_path=args.manifest.resolve(),
        wallets=selected,
        gateway=args.gateway,
        per_wallet_atomic=per_wallet_atomic,
        target_balance_atomic=target_balance_atomic,
    )

    output = ensure_work_path(
        (args.output or (args.manifest.resolve().parent / "plans" / f"{stamp_utc()}-{args.label}.json")).resolve()
    )
    payload = {
        "createdAt": now_utc(),
        "label": args.label,
        "manifest": str(args.manifest.resolve()),
        "walletCount": len(selected),
        "plannedEntryCount": len(entries),
        "gateway": args.gateway,
        "mode": "flat" if per_wallet_atomic is not None else "topup",
        "perWalletAtomic": per_wallet_atomic,
        "perWalletEgld": egld_from_atomic(per_wallet_atomic) if per_wallet_atomic is not None else None,
        "targetBalanceAtomic": target_balance_atomic,
        "targetBalanceEgld": egld_from_atomic(target_balance_atomic) if target_balance_atomic is not None else None,
        "totalAtomic": sum(entry.amount_atomic for entry in entries),
        "totalEgld": egld_from_atomic(sum(entry.amount_atomic for entry in entries)),
        "entries": [entry.to_dict() for entry in entries],
        "manifestCreatedAt": manifest_meta.get("createdAt"),
    }
    atomic_write_json(output, payload)
    print(f"wrote funding plan: {output}")
    print(f"planned total: {payload['totalEgld']} EGLD across {len(entries)} wallets")


def send_funding_batches_sequential(
    *,
    gateway: str,
    leader_address: str,
    batches: Sequence[BatchEnvelope],
    summary_path: Path,
    summary: dict[str, object],
    dry_run: bool,
    wait_for_nonce_advance: bool,
    nonce_timeout_seconds: int,
    nonce_poll_seconds: float,
) -> None:
    for batch in batches:
        response = submit_batch(gateway, batch, dry_run)
        summary["counts"]["batchesCompleted"] += 1
        returned_hashes = response.get("returnedHashes", [])
        accepted_in_batch = count_nonempty_hashes(returned_hashes)
        if response.get("error") is not None:
            summary["counts"]["ambiguousTransactions"] += len(batch.records)
        else:
            summary["counts"]["acceptedTransactions"] += accepted_in_batch
            summary["counts"]["notAcceptedTransactions"] += len(batch.records) - accepted_in_batch
        update_run_summary(summary_path, summary)
        for index, record in enumerate(batch.records):
            gateway_hash = returned_hashes[index] if index < len(returned_hashes) else None
            if response.get("error") is not None:
                submission_state = "ambiguous"
            elif str(gateway_hash or "").strip():
                submission_state = "accepted"
            else:
                submission_state = "notAccepted"
            append_ndjson(
                summary_path.parent / "txs.ndjson",
                {
                    "recordedAt": now_utc(),
                    "batchId": batch.batch_id,
                    "submissionState": submission_state,
                    "sender": record.sender_address,
                    "receiver": record.receiver_address,
                    "nonce": record.nonce,
                    "predictedHash": record.predicted_hash,
                    "gatewayHash": gateway_hash,
                    "plannedFeeAtomic": record.planned_fee_atomic,
                },
            )
        if response.get("error") is not None:
            summary["stoppedOnBatchId"] = batch.batch_id
            summary["stoppedReason"] = "batch-error"
            update_run_summary(summary_path, summary)
            break
        if accepted_in_batch != len(batch.records):
            summary["stoppedOnBatchId"] = batch.batch_id
            summary["stoppedReason"] = "partial-acceptance"
            update_run_summary(summary_path, summary)
            break
        if wait_for_nonce_advance and not dry_run:
            target_nonce = batch.records[-1].nonce + 1
            last_nonce, _ = wait_for_account_nonce(
                gateway,
                leader_address,
                target_nonce,
                nonce_timeout_seconds,
                nonce_poll_seconds,
            )
            summary["leaderNonceAfterLastBatch"] = last_nonce
            update_run_summary(summary_path, summary)


def command_fund_wallets(args: argparse.Namespace) -> None:
    plan = json.loads(require_file(args.plan.resolve()).read_text())
    leader_signer = signer_from_pem(args.leader_pem.resolve())
    leader_address = address_from_signer(leader_signer)
    entries = plan["entries"]
    total_atomic = sum(int(entry["amountAtomic"]) for entry in entries)
    fee_atomic = len(entries) * planned_fee_atomic(args.gas_price)
    required = total_atomic + fee_atomic
    if args.dry_run:
        leader_nonce, leader_balance = 0, required
    else:
        leader_nonce, leader_balance = fetch_account_nonce_and_balance(args.gateway, leader_address)
    if leader_balance < required:
        raise SystemExit(f"leader balance {leader_balance} is below required {required}")

    run_dir = create_run_dir(WORK_ROOT / "runs" / "funding", args.label)
    batches_dir = ensure_dir(run_dir / "batches")
    summary_path = run_dir / "run.json"
    summary = {
        "kind": "fund-wallets",
        "createdAt": now_utc(),
        "leader": leader_address,
        "plan": str(args.plan.resolve()),
        "dryRun": args.dry_run,
        "counts": {
            "batchesPlanned": 0,
            "batchesCompleted": 0,
            "acceptedTransactions": 0,
            "notAcceptedTransactions": 0,
            "ambiguousTransactions": 0,
        },
        "gasPrice": args.gas_price,
        "batchSize": args.batch_size,
        "totalAtomic": total_atomic,
        "totalEgld": egld_from_atomic(total_atomic),
    }
    update_run_summary(summary_path, summary)

    computer = TransactionComputer()
    factory = build_transfer_factory()
    batch_records: list[PreparedTx] = []
    envelopes: list[BatchEnvelope] = []
    nonce = leader_nonce
    batch_id = 0
    for entry in entries:
        receiver = entry["address"]
        tx = factory.create_transaction_for_native_token_transfer(
            sender=Address.new_from_bech32(leader_address),
            receiver=Address.new_from_bech32(receiver),
            native_amount=int(entry["amountAtomic"]),
        )
        tx.nonce = nonce
        tx.gas_price = args.gas_price
        tx.gas_limit = MOVE_GAS_LIMIT
        tx.signature = leader_signer.sign(computer.compute_bytes_for_signing(tx))
        record = PreparedTx(
            sender_address=leader_address,
            receiver_address=receiver,
            sender_shard=SHARD_COMPUTER.get_shard_of_address(Address.new_from_bech32(leader_address)),
            receiver_shard=SHARD_COMPUTER.get_shard_of_address(Address.new_from_bech32(receiver)),
            nonce=nonce,
            value_atomic=int(entry["amountAtomic"]),
            gas_price=args.gas_price,
            gas_limit=MOVE_GAS_LIMIT,
            planned_fee_atomic=planned_fee_atomic(args.gas_price),
            predicted_hash=computer.compute_transaction_hash(tx).hex(),
            transaction_dict=tx.to_dictionary(),
            transaction=tx,
        )
        batch_records.append(record)
        nonce += 1
        if len(batch_records) == args.batch_size:
            batch_id += 1
            batch = BatchEnvelope(
                batch_id=batch_id,
                planned_at=now_utc(),
                batch_file=batches_dir / f"{batch_id:06d}-planned.json",
                response_file=batches_dir / f"{batch_id:06d}-response.json",
                records=batch_records,
            )
            atomic_write_json(batch.batch_file, planned_batch_payload(batch, args.dry_run))
            envelopes.append(batch)
            summary["counts"]["batchesPlanned"] += 1
            batch_records = []
    if batch_records:
        batch_id += 1
        batch = BatchEnvelope(
            batch_id=batch_id,
            planned_at=now_utc(),
            batch_file=batches_dir / f"{batch_id:06d}-planned.json",
            response_file=batches_dir / f"{batch_id:06d}-response.json",
            records=batch_records,
        )
        atomic_write_json(batch.batch_file, planned_batch_payload(batch, args.dry_run))
        envelopes.append(batch)
        summary["counts"]["batchesPlanned"] += 1

    update_run_summary(summary_path, summary)
    send_funding_batches_sequential(
        gateway=args.gateway,
        leader_address=leader_address,
        batches=envelopes,
        summary_path=summary_path,
        summary=summary,
        dry_run=args.dry_run,
        wait_for_nonce_advance=args.wait_for_nonce_advance,
        nonce_timeout_seconds=args.nonce_timeout_seconds,
        nonce_poll_seconds=args.nonce_poll_seconds,
    )
    summary["completedAt"] = now_utc()
    update_run_summary(summary_path, summary)
    print(f"funding run directory: {run_dir}")


def command_run_window(args: argparse.Namespace) -> None:
    _, wallets = load_manifest(args.manifest.resolve())
    selected = filter_wallets(wallets, args.wallet_limit, args.sender_shards)
    wait_until(args.wait_until)
    budget_atomic = args.budget_atomic or (atomic_from_egld(args.budget_egld) if args.budget_egld else None)
    run_dir = execute_sender_run(
        manifest_path=args.manifest.resolve(),
        wallets=selected,
        label=args.label,
        gateway=args.gateway,
        api=args.api,
        receiver_mode=args.receiver_mode,
        tx_value_atomic=args.tx_value_atomic,
        gas_price=args.gas_price,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        inflight_nonces_per_sender=args.inflight_nonces_per_sender,
        duration_seconds=args.duration_seconds,
        stop_at=args.stop_at,
        stop_seconds_early=args.stop_seconds_early,
        budget_atomic=budget_atomic,
        halt_on_ambiguous_batch=args.halt_on_ambiguous_batch,
        dry_run=args.dry_run,
        run_parent=WORK_ROOT / "runs" / "live",
        run_kind="run-window",
    )
    print(f"run directory: {run_dir}")


def command_calibrate(args: argparse.Namespace) -> None:
    _, wallets = load_manifest(args.manifest.resolve())
    selected = filter_wallets(wallets, args.wallet_limit, args.sender_shards)
    run_dir = execute_sender_run(
        manifest_path=args.manifest.resolve(),
        wallets=selected,
        label=args.label,
        gateway=args.gateway,
        api=args.api,
        receiver_mode=args.receiver_mode,
        tx_value_atomic=args.tx_value_atomic,
        gas_price=args.gas_price,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        inflight_nonces_per_sender=args.inflight_nonces_per_sender,
        duration_seconds=args.duration_seconds,
        stop_at=None,
        stop_seconds_early=args.stop_seconds_early,
        budget_atomic=args.budget_atomic or (atomic_from_egld(args.budget_egld) if args.budget_egld else None),
        halt_on_ambiguous_batch=args.halt_on_ambiguous_batch,
        dry_run=args.dry_run,
        run_parent=WORK_ROOT / "runs" / "calibration",
        run_kind="calibrate",
    )
    if args.settle_seconds > 0 and not args.dry_run:
        print(f"settling for {args.settle_seconds}s before reporting", flush=True)
        time.sleep(args.settle_seconds)
    if not args.dry_run:
        report = report_run(run_dir, args.api, args.report_workers, args.sample_size)
        print(json.dumps(report, indent=2))
    else:
        print(f"dry-run calibration directory: {run_dir}")


def render_sweep_markdown(entries: Sequence[dict[str, object]]) -> str:
    lines = [
        "# Sweep Summary",
        "",
        "| Label | Gas Price | Batch | Workers | Inflight | Accepted | Success | Pending | Accepted tx/s | Confirmed tx/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for entry in entries:
        report = entry.get("report", {})
        counts = report.get("counts", {})
        rates = report.get("rates", {})
        lines.append(
            "| {label} | {gas_price} | {batch_size} | {workers} | {inflight} | {accepted} | {success} | {pending} | {accepted_tps} | {confirmed_tps} |".format(
                label=entry["label"],
                gas_price=entry["gasPrice"],
                batch_size=entry["batchSize"],
                workers=entry["numWorkers"],
                inflight=entry["inflightNoncesPerSender"],
                accepted=counts.get("accepted", 0),
                success=counts.get("success", 0),
                pending=counts.get("pending", 0),
                accepted_tps=f"{rates.get('acceptedTxPerSec', 0) or 0:.2f}",
                confirmed_tps=f"{rates.get('confirmedTxPerSec', 0) or 0:.2f}",
            )
        )
    lines.append("")
    return "\n".join(lines)


def command_sweep(args: argparse.Namespace) -> None:
    _, wallets = load_manifest(args.manifest.resolve())
    selected = filter_wallets(wallets, args.wallet_limit, args.sender_shards)
    sweep_dir = create_run_dir(WORK_ROOT / "sweeps", args.label)
    entries: list[dict[str, object]] = []
    combinations = list(
        itertools.product(
            args.gas_price_multipliers,
            args.batch_sizes,
            args.worker_counts,
            args.inflight_depths,
        )
    )
    if args.limit_configs is not None:
        combinations = combinations[: args.limit_configs]

    for multiplier, batch_size, workers, inflight in combinations:
        gas_price = int(round(args.base_gas_price * multiplier))
        label = f"gp{multiplier:g}-b{batch_size}-w{workers}-d{inflight}"
        print(f"running sweep config {label}", flush=True)
        run_dir = execute_sender_run(
            manifest_path=args.manifest.resolve(),
            wallets=selected,
            label=label,
            gateway=args.gateway,
            api=args.api,
            receiver_mode=args.receiver_mode,
            tx_value_atomic=args.tx_value_atomic,
            gas_price=gas_price,
            batch_size=batch_size,
            num_workers=workers,
            inflight_nonces_per_sender=inflight,
            duration_seconds=args.duration_seconds,
            stop_at=None,
            stop_seconds_early=args.stop_seconds_early,
            budget_atomic=args.budget_atomic or (atomic_from_egld(args.budget_egld) if args.budget_egld else None),
            halt_on_ambiguous_batch=args.halt_on_ambiguous_batch,
            dry_run=args.dry_run,
            run_parent=sweep_dir / "runs",
            run_kind="sweep-calibration",
        )
        report = None
        if not args.dry_run:
            if args.settle_seconds > 0:
                time.sleep(args.settle_seconds)
            report = report_run(run_dir, args.api, args.report_workers, args.sample_size)
        entries.append(
            {
                "label": label,
                "runDir": str(run_dir),
                "gasPrice": gas_price,
                "batchSize": batch_size,
                "numWorkers": workers,
                "inflightNoncesPerSender": inflight,
                "report": report,
            }
        )
        atomic_write_json(sweep_dir / "summary.json", {"createdAt": now_utc(), "entries": entries})
        atomic_write_text(sweep_dir / "summary.md", render_sweep_markdown(entries))
        if args.cooldown_seconds > 0 and not args.dry_run:
            time.sleep(args.cooldown_seconds)

    print(f"sweep directory: {sweep_dir}")


def command_report_run(args: argparse.Namespace) -> None:
    run_dir = ensure_work_path(args.run_dir.resolve())
    report = report_run(run_dir, args.api, args.workers, args.sample_size)
    print(json.dumps(report, indent=2))


def add_manifest_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, required=True)


def add_wallet_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--wallet-limit", type=int)
    parser.add_argument("--sender-shards", type=parse_shard_csv)


def add_sender_tuning_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gas-price", type=int, default=MIN_GAS_PRICE)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--inflight-nonces-per-sender", type=int, default=32)
    parser.add_argument("--receiver-mode", choices=["same-shard-ring", "cross-shard-ring"], default=DEFAULT_RECEIVER_MODE)
    parser.add_argument("--tx-value-atomic", type=int, default=MOVE_VALUE_ATOMIC)
    parser.add_argument("--budget-egld")
    parser.add_argument("--budget-atomic", type=int)
    parser.add_argument("--stop-seconds-early", type=int, default=10)
    parser.add_argument("--halt-on-ambiguous-batch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")


def add_endpoint_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gateway", default=DEFAULT_GATEWAY)
    parser.add_argument("--api", default=DEFAULT_API)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generic high-throughput MoveBalance transaction sprint harness")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate-wallets", help="Generate a fresh shard-aware sender wallet set")
    generate.add_argument("--count", type=int, default=500)
    generate.add_argument("--output-dir", type=Path, default=WORK_ROOT / "wallet-sets" / "tx-sprint-500")
    generate.add_argument("--prefix", default="sprint")
    generate.add_argument("--layout", choices=["balanced", "single-shard"], default="balanced")
    generate.add_argument("--shards", type=parse_shard_csv, default=(0, 1, 2))
    generate.add_argument("--shard", type=int, default=0)
    generate.add_argument("--overwrite", action="store_true")
    generate.add_argument("--mxpy", type=Path, default=DEFAULT_MXPY)
    add_endpoint_arguments(generate)
    generate.set_defaults(func=command_generate_wallets)

    plan = sub.add_parser("plan-funding", help="Generate a funding manifest from the leader wallet")
    add_manifest_argument(plan)
    add_wallet_filter_arguments(plan)
    plan.add_argument("--label", default="funding-plan")
    plan.add_argument("--amount-egld")
    plan.add_argument("--amount-atomic", type=int)
    plan.add_argument("--target-balance-egld")
    plan.add_argument("--target-balance-atomic", type=int)
    plan.add_argument("--output", type=Path)
    plan.add_argument("--gateway", default=DEFAULT_GATEWAY)
    plan.set_defaults(func=command_plan_funding)

    fund = sub.add_parser("fund-wallets", help="Execute a funding manifest from the leader wallet")
    fund.add_argument("--plan", type=Path, required=True)
    fund.add_argument("--leader-pem", type=Path, required=True)
    fund.add_argument("--label", default="fund-wallets")
    fund.add_argument("--gas-price", type=int, default=MIN_GAS_PRICE)
    fund.add_argument("--batch-size", type=int, default=100)
    fund.add_argument("--wait-for-nonce-advance", action=argparse.BooleanOptionalAction, default=True)
    fund.add_argument("--nonce-timeout-seconds", type=int, default=180)
    fund.add_argument("--nonce-poll-seconds", type=float, default=2.0)
    fund.add_argument("--dry-run", action="store_true")
    fund.add_argument("--gateway", default=DEFAULT_GATEWAY)
    fund.set_defaults(func=command_fund_wallets)

    run_window = sub.add_parser("run-window", help="Run a live or rehearsal MoveBalance sender window")
    add_manifest_argument(run_window)
    add_wallet_filter_arguments(run_window)
    add_endpoint_arguments(run_window)
    add_sender_tuning_arguments(run_window)
    run_window.add_argument("--label", default="window-run")
    run_window.add_argument("--wait-until")
    run_window.add_argument("--duration-seconds", type=int)
    run_window.add_argument("--stop-at")
    run_window.set_defaults(func=command_run_window)

    calibrate = sub.add_parser("calibrate", help="Run a short calibration chunk and auto-report")
    add_manifest_argument(calibrate)
    add_wallet_filter_arguments(calibrate)
    add_endpoint_arguments(calibrate)
    add_sender_tuning_arguments(calibrate)
    calibrate.add_argument("--label", default="calibration")
    calibrate.add_argument("--duration-seconds", type=int, default=180)
    calibrate.add_argument("--settle-seconds", type=int, default=45)
    calibrate.add_argument("--report-workers", type=int, default=16)
    calibrate.add_argument("--sample-size", type=int, default=20)
    calibrate.set_defaults(func=command_calibrate)

    sweep = sub.add_parser("sweep", help="Run a structured calibration sweep across sender parameters")
    add_manifest_argument(sweep)
    add_wallet_filter_arguments(sweep)
    add_endpoint_arguments(sweep)
    sweep.add_argument("--label", default="sweep")
    sweep.add_argument("--duration-seconds", type=int, default=120)
    sweep.add_argument("--base-gas-price", type=int, default=MIN_GAS_PRICE)
    sweep.add_argument("--gas-price-multipliers", type=parse_float_csv, default=(1.0, 1.25, 1.5, 2.0))
    sweep.add_argument("--batch-sizes", type=parse_int_csv, default=(100, 250, 500))
    sweep.add_argument("--worker-counts", type=parse_int_csv, default=(4, 8, 12))
    sweep.add_argument("--inflight-depths", type=parse_int_csv, default=(16, 32, 64))
    sweep.add_argument("--receiver-mode", choices=["same-shard-ring", "cross-shard-ring"], default=DEFAULT_RECEIVER_MODE)
    sweep.add_argument("--tx-value-atomic", type=int, default=MOVE_VALUE_ATOMIC)
    sweep.add_argument("--budget-egld")
    sweep.add_argument("--budget-atomic", type=int)
    sweep.add_argument("--stop-seconds-early", type=int, default=10)
    sweep.add_argument("--halt-on-ambiguous-batch", action="store_true")
    sweep.add_argument("--dry-run", action="store_true")
    sweep.add_argument("--settle-seconds", type=int, default=45)
    sweep.add_argument("--cooldown-seconds", type=int, default=15)
    sweep.add_argument("--report-workers", type=int, default=16)
    sweep.add_argument("--sample-size", type=int, default=20)
    sweep.add_argument("--limit-configs", type=int)
    sweep.set_defaults(func=command_sweep)

    report = sub.add_parser("report-run", help="Verify a run directory and compute outcome metrics")
    report.add_argument("--run-dir", type=Path, required=True)
    report.add_argument("--api", default=DEFAULT_API)
    report.add_argument("--workers", type=int, default=16)
    report.add_argument("--sample-size", type=int, default=20)
    report.set_defaults(func=command_report_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
