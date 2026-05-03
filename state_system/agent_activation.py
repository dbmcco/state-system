from __future__ import annotations

from state_system.agent_consumers import render_package_for_agent
from state_system.contracts import validate_schema
from state_system.stores import JsonObject, StateStoreBundle


class AgentActivationValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("agent activation validation failed")
        self.errors = tuple(errors)


def create_agent_activation(
    stores: StateStoreBundle,
    schemas: dict[str, JsonObject],
    *,
    package_id: str,
    consumer_ref: str,
    created_at: str,
    activation_goal: str,
    expected_response_type: str,
    activation_id: str | None = None,
) -> JsonObject:
    package = stores.context_packages.read(package_id)
    activation = {
        "id": activation_id
        or _default_activation_id(
            package_id=package_id,
            consumer_ref=consumer_ref,
            created_at=created_at,
        ),
        "type": "agent_activation",
        "package_id": package_id,
        "consumer_ref": consumer_ref,
        "created_at": created_at,
        "activation_goal": activation_goal,
        "expected_response_type": expected_response_type,
        "allowed_action_refs": _action_refs(package, approval_required=False),
        "prohibited_action_refs": _action_refs(package, approval_required=True),
        "evidence_refs": _evidence_refs(package),
        "freshness": dict(package.get("freshness", {})),
        "capture_policy": {
            "mode": "capture_required",
            "store_raw_response": True,
            "response_becomes_truth": False,
            "next_review_required": True,
        },
        "instructions": [
            "Use only the attached State System package as your working context.",
            "Do not take external action from this activation.",
            "Treat prohibited actions as unavailable unless a future activation changes them.",
            "Return a response matching the expected response type.",
        ],
    }
    errors = validate_schema(activation, schemas["agent_activation"])
    if errors:
        raise AgentActivationValidationError(errors)
    stores.agent_activations.create(activation)
    return activation


def render_activation_for_agent(stores: StateStoreBundle, activation_id: str) -> str:
    activation = stores.agent_activations.read(activation_id)
    package = stores.context_packages.read(activation["package_id"])
    lines = [
        "State System Agent Activation",
        f"Activation: {activation['id']}",
        f"Consumer: {activation['consumer_ref']}",
        f"Created at: {activation['created_at']}",
        f"Goal: {activation['activation_goal']}",
        f"Expected response type: {activation['expected_response_type']}",
        "",
    ]
    _append_list(lines, "Allowed action refs", activation["allowed_action_refs"])
    _append_list(lines, "Prohibited action refs", activation["prohibited_action_refs"])
    _append_list(lines, "Activation evidence refs", activation["evidence_refs"])
    lines.extend(
        [
            "Capture policy:",
            f"- Mode: {activation['capture_policy']['mode']}",
            f"- Store raw response: {activation['capture_policy']['store_raw_response']}",
            f"- Response becomes truth: {activation['capture_policy']['response_becomes_truth']}",
            f"- Next review required: {activation['capture_policy']['next_review_required']}",
            "",
        ]
    )
    _append_list(lines, "Activation instructions", activation["instructions"])
    lines.extend(["", render_package_for_agent(package)])
    return "\n".join(lines).rstrip()


def _action_refs(package: JsonObject, *, approval_required: bool) -> list[str]:
    refs: list[str] = []
    for action in package.get("available_actions", []):
        if bool(action.get("approval_required")) == approval_required:
            refs.append(action["id"])
    return refs


def _evidence_refs(package: JsonObject) -> list[str]:
    refs = [package["id"]]
    refs.extend(package.get("evidence_context", {}).get("evidence_refs", []))
    seen: set[str] = set()
    unique: list[str] = []
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        unique.append(ref)
    return unique


def _default_activation_id(
    *,
    package_id: str,
    consumer_ref: str,
    created_at: str,
) -> str:
    stamp = created_at.replace("+00:00", "Z")
    stamp = stamp.replace("-", "").replace(":", "").replace(".", "")
    return f"activation.{package_id}.{consumer_ref}.{stamp}"


def _append_list(lines: list[str], title: str, values: list[object]) -> None:
    lines.append(f"{title}:")
    if not values:
        lines.append("- None.")
    else:
        for value in values:
            lines.append(f"- {value}")
    lines.append("")
