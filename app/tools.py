"""T7: calculate_expense_approval. Deterministic rules from expense_reimbursement_policy.pdf (v2.0, 2026-01-01).
Called by the chat pipeline (not chosen by the LLM) so the arithmetic is never left to a 3B model."""
from __future__ import annotations
import re

SOURCE = "expense_reimbursement_policy.pdf"
CFO_ABOVE = 25_000  # any single claim above this also needs the CFO
# type -> (keywords, limit in BDT, unit, label)
LIMITS = {
    "transport": (r"transport|ride.?share|cng|uber|pathao|taxi", 1500, "day", "local transport"),
    "meal": (r"\bmeals?\b|lunch|dinner|client visit", 800, "person", "meals during client visits"),
    "hotel": (r"hotel|accommodation|\bnights?\b", 6000, "night", "hotel outside Dhaka"),
    "internet": (r"internet|broadband|wi.?fi", 1000, "month", "internet allowance (remote work)"),
    "mobile": (r"mobile|phone bill|\bphone\b", 700, "month", "mobile phone bill"),
}
NOT_REIMBURSABLE = "Alcohol, traffic/parking fines, personal entertainment and expenses without a receipt are not reimbursable."
_UNIT = {"day": r"days?", "person": r"persons?|people|pax", "night": r"nights?", "month": r"months?"}


def detect_type(text: str) -> str | None:
    for key, (kw, *_rest) in LIMITS.items():
        if re.search(kw, text, re.I):
            return key
    return None


def calculate_expense_approval(amount: float, expense_type: str | None = None, quantity: int = 1) -> dict:
    """Who must approve a single claim of `amount` BDT. quantity = nights/days/persons/months when the limit is per unit."""
    approvers, notes = [], []
    limit_total = None
    if expense_type in LIMITS:
        _, per_unit, unit, label = LIMITS[expense_type]
        limit_total = per_unit * max(1, quantity)
    if amount > CFO_ABOVE:
        approvers = ["Department head", "CFO"]
        notes.append(f"Single claim above BDT {CFO_ABOVE:,}: the CFO must also approve.")
    elif limit_total is not None:
        approvers = ["Team lead"] if amount <= limit_total else ["Department head"]
        notes.append(f"Limit for {label}: BDT {per_unit:,} per {unit}"
                     f"{f' x {quantity} = BDT {limit_total:,}' if quantity > 1 else ''}; claim is "
                     f"{'within' if amount <= limit_total else 'above'} it.")
        if expense_type == "hotel":
            notes.append("Hotel stays need the team lead's pre-approval.")
    else:
        approvers = ["Team lead if within the limit for its expense type", "Department head if above a limit"]
        notes.append("Limits: transport BDT 1,500/day, meals BDT 800/person, hotel BDT 6,000/night, "
                     "internet BDT 1,000/month, mobile BDT 700/month.")
    notes.append("Submit via NodiHR > Expenses within 30 days with a receipt. " + NOT_REIMBURSABLE)
    return {"amount": amount, "expense_type": expense_type, "quantity": quantity,
            "limit_total": limit_total, "approvers": approvers, "notes": notes}


_ASK = re.compile(r"approv|authori[sz]|sign.?off|who (must|needs?|has to|should)|claim", re.I)
_AMT = re.compile(r"(?:bdt|tk\.?|taka|৳)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:bdt|tk\b|taka|৳)|"
                  r"\bclaim\w*\s+(?:of\s+|for\s+)?([\d,]{3,})", re.I)


def parse_question(text: str) -> tuple[float, str | None, int] | None:
    """(amount, expense_type, quantity) if the question asks about approval of a BDT amount, else None."""
    if not _ASK.search(text):
        return None
    m = _AMT.search(text)
    if not m:
        return None
    amount = float((m.group(1) or m.group(2) or m.group(3)).replace(",", ""))
    etype = detect_type(text)
    qty = 1
    if etype:
        u = re.search(rf"(\d+)\s*(?:{_UNIT[LIMITS[etype][2]]})", text, re.I)
        qty = int(u.group(1)) if u else 1
    return amount, etype, qty


def tool_context(text: str) -> tuple[dict, str] | None:
    """If `text` is an approval question: (result, plain-text fact block for the prompt)."""
    parsed = parse_question(text)
    if not parsed:
        return None
    r = calculate_expense_approval(*parsed)
    fact = (f"Approval calculation (policy section 3) for a claim of BDT {r['amount']:,.0f}"
            f"{' for ' + LIMITS[r['expense_type']][3] if r['expense_type'] else ''}: "
            f"approval needed from: {'; '.join(r['approvers'])}. " + " ".join(r["notes"]))
    return r, fact
