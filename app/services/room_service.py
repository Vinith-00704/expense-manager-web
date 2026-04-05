from datetime import date
from typing import List, Tuple, Optional

from ..extensions import db
from ..models.room import Room, RoomMember, RoomExpense, RoomExpenseParticipant
from ..models.user import User


def create_room(user_id: int, name: str, description: str = "") -> dict:
    room = Room(owner_id=user_id, name=name.strip(), description=description)
    db.session.add(room)
    db.session.flush()
    # add owner as member
    db.session.add(RoomMember(room_id=room.id, user_id=user_id, role="owner"))
    db.session.commit()
    return _room_detail(room, user_id)


def list_rooms(user_id: int) -> List[dict]:
    rooms = (
        Room.query.join(RoomMember, RoomMember.room_id == Room.id)
        .filter(RoomMember.user_id == user_id, Room.is_active == True)
        .order_by(Room.created_at.desc())
        .all()
    )
    return [_room_detail(r, user_id) for r in rooms]


def _room_detail(room: Room, user_id: int) -> dict:
    d = room.to_dict()
    d["member_count"] = room.members.count()
    total = sum(float(e.amount) for e in room.expenses)
    d["total_spent"] = round(total, 2)
    d["is_owner"] = room.owner_id == user_id
    return d


def get_room(user_id: int, room_id: int) -> dict:
    room = _assert_member(user_id, room_id)
    d = _room_detail(room, user_id)
    d["members"] = get_members(room_id)
    return d


def add_member_by_username(room_id: int, requesting_user_id: int, username: str) -> dict:
    _assert_owner(requesting_user_id, room_id)
    user = User.query.filter_by(username=username.strip().lower()).first()
    if not user:
        raise ValueError("Username not found")
    existing = RoomMember.query.filter_by(room_id=room_id, user_id=user.id).first()
    if existing:
        raise ValueError("User is already a member")
    db.session.add(RoomMember(room_id=room_id, user_id=user.id, role="member"))
    db.session.commit()
    return {"id": user.id, "username": user.username, "full_name": user.full_name}


def get_members(room_id: int) -> List[dict]:
    members = (
        RoomMember.query.filter_by(room_id=room_id)
        .join(User, User.id == RoomMember.user_id)
        .with_entities(User.id, User.username, User.full_name, RoomMember.role)
        .all()
    )
    return [{"id": m.id, "username": m.username, "full_name": m.full_name, "role": m.role} for m in members]


def add_room_expense(room_id: int, user_id: int, data: dict, member_ids: List[int]) -> dict:
    from ..utils.validators import validate_amount, validate_date
    _assert_member(user_id, room_id)
    if not member_ids:
        raise ValueError("Select at least one participant")
    amount = validate_amount(data["amount"])
    share = round(amount / len(member_ids), 2)
    exp = RoomExpense(
        room_id=room_id, paid_by=user_id,
        description=data["description"],
        amount=amount,
        expense_date=validate_date(data["expense_date"]),
    )
    db.session.add(exp)
    db.session.flush()
    for mid in member_ids:
        db.session.add(RoomExpenseParticipant(expense_id=exp.id, user_id=mid, share_amount=share))
    db.session.commit()
    return exp.to_dict()


def get_ledger(room_id: int) -> List[dict]:
    expenses = RoomExpense.query.filter_by(room_id=room_id).order_by(RoomExpense.expense_date.desc()).all()
    result = []
    for e in expenses:
        payer = User.query.get(e.paid_by)
        d = e.to_dict()
        d["payer_name"] = payer.full_name if payer else "Unknown"
        result.append(d)
    return result


def get_settlements(room_id: int) -> List[dict]:
    members = get_members(room_id)
    if not members:
        return []
    member_ids = [m["id"] for m in members]
    name_map = {m["id"]: m["full_name"] for m in members}

    paid: dict = {mid: 0.0 for mid in member_ids}
    for e in RoomExpense.query.filter_by(room_id=room_id).all():
        paid[e.paid_by] = paid.get(e.paid_by, 0) + float(e.amount)

    owed: dict = {mid: 0.0 for mid in member_ids}
    for p in (
        RoomExpenseParticipant.query
        .join(RoomExpense, RoomExpense.id == RoomExpenseParticipant.expense_id)
        .filter(RoomExpense.room_id == room_id)
        .all()
    ):
        owed[p.user_id] = owed.get(p.user_id, 0) + float(p.share_amount)

    net = {mid: paid.get(mid, 0) - owed.get(mid, 0) for mid in member_ids}
    return _settle(net, name_map)


def _settle(net: dict, name_map: dict) -> List[dict]:
    creditors = sorted([(uid, amt) for uid, amt in net.items() if amt > 0.009], key=lambda x: -x[1])
    debtors = sorted([(uid, -amt) for uid, amt in net.items() if amt < -0.009], key=lambda x: -x[1])
    settlements = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        did, need = debtors[i]
        cid, owed = creditors[j]
        pay = round(min(need, owed), 2)
        settlements.append({"from": name_map[did], "to": name_map[cid], "amount": pay})
        need -= pay; owed -= pay
        if need < 0.01: i += 1
        else: debtors[i] = (did, need)
        if owed < 0.01: j += 1
        else: creditors[j] = (cid, owed)
    return settlements


def delete_room(user_id: int, room_id: int) -> None:
    room = _assert_owner(user_id, room_id)
    room.is_active = False
    db.session.commit()


def _assert_member(user_id: int, room_id: int) -> Room:
    room = Room.query.get_or_404(room_id)
    if not RoomMember.query.filter_by(room_id=room_id, user_id=user_id).first():
        from flask import abort; abort(403)
    return room


def _assert_owner(user_id: int, room_id: int) -> Room:
    room = Room.query.get_or_404(room_id)
    if room.owner_id != user_id:
        from flask import abort; abort(403)
    return room
