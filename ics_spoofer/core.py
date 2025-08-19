import base64
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple


RFC5545_MAX_LINE_OCTETS = 75


def _escape_text(value: str) -> str:
    if value is None:
        return ""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold_ical_line(line: str) -> str:
    # Fold to 75 octets per RFC 5545 using CRLF and space continuation
    bytes_line = line.encode("utf-8")
    if len(bytes_line) <= RFC5545_MAX_LINE_OCTETS:
        return line

    parts: List[bytes] = []
    start = 0
    while start < len(bytes_line):
        end = start + RFC5545_MAX_LINE_OCTETS
        if end >= len(bytes_line):
            parts.append(bytes_line[start:])
            break
        # Avoid splitting in the middle of a multi-byte UTF-8 sequence
        while end > start and (bytes_line[end] & 0xC0) == 0x80:
            end -= 1
        parts.append(bytes_line[start:end])
        start = end
    # Join with CRLF + space prefix for continuations
    folded = parts[0]
    for cont in parts[1:]:
        folded += b"\r\n " + cont
    return folded.decode("utf-8")


def _format_dt_utc(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def _parse_iso_dt(value: str) -> datetime:
    s = value.strip()
    # Accept trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # Accept date only as all-day start at 00:00Z
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return datetime.fromisoformat(s + "T00:00:00+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise ValueError(f"Invalid datetime format: {value}. Use ISO 8601, e.g., 2025-01-20T10:00:00Z")


@dataclass
class Organizer:
    common_name: str
    email: str


@dataclass
class Attendee:
    common_name: str
    email: str
    partstat: str = "NEEDS-ACTION"
    role: str = "REQ-PARTICIPANT"
    rsvp: str = "FALSE"


@dataclass
class AttachmentSpec:
    path: str
    mime_type: Optional[str] = None
    label: Optional[str] = None


def _format_organizer(organizer: Organizer) -> List[str]:
    cn = _escape_text(organizer.common_name)
    return [
        _fold_ical_line(f"ORGANIZER;CN={cn}:mailto:{organizer.email}")
    ]


def _format_attendee(attendee: Attendee) -> List[str]:
    cn = _escape_text(attendee.common_name)
    params = [
        f"CN={cn}",
        f"ROLE={attendee.role}",
        f"PARTSTAT={attendee.partstat}",
        f"RSVP={attendee.rsvp}",
    ]
    line = f"ATTENDEE;{';'.join(params)}:mailto:{attendee.email}"
    return [_fold_ical_line(line)]


def _read_file_base64(path: str) -> Tuple[str, str]:
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    return b64, str(len(data))


def _format_attachment(spec: AttachmentSpec) -> List[str]:
    b64, _ = _read_file_base64(spec.path)
    params: List[str] = ["ENCODING=BASE64", "VALUE=BINARY"]
    if spec.mime_type:
        params.insert(0, f"FMTTYPE={spec.mime_type}")
    if spec.label:
        params.append(f"X-LABEL={_escape_text(spec.label)}")
    prefix = f"ATTACH;{';'.join(params)}:"
    # Split the base64 into folded lines, but ensure property folding rules
    first_line = prefix + b64
    return [_fold_ical_line(first_line)]


@dataclass
class EventSpec:
    summary: str
    description: Optional[str]
    location: Optional[str]
    start: datetime
    end: datetime
    organizer: Optional[Organizer]
    attendees: List[Attendee]
    attachments: List[AttachmentSpec]
    uid: str
    prodid: str
    method: str


def build_ics(spec: EventSpec) -> str:
    lines: List[str] = []
    lines.append("BEGIN:VCALENDAR")
    lines.append(_fold_ical_line(f"PRODID:{_escape_text(spec.prodid)}"))
    lines.append("VERSION:2.0")
    lines.append(_fold_ical_line(f"METHOD:{spec.method}"))
    lines.append("CALSCALE:GREGORIAN")

    lines.append("BEGIN:VEVENT")
    lines.append(f"UID:{spec.uid}")
    lines.append(f"DTSTAMP:{_format_dt_utc(datetime.now(timezone.utc))}")
    lines.append(f"DTSTART:{_format_dt_utc(spec.start)}")
    lines.append(f"DTEND:{_format_dt_utc(spec.end)}")
    lines.append(_fold_ical_line(f"SUMMARY:{_escape_text(spec.summary)}"))
    if spec.description:
        lines.append(_fold_ical_line(f"DESCRIPTION:{_escape_text(spec.description)}"))
    if spec.location:
        lines.append(_fold_ical_line(f"LOCATION:{_escape_text(spec.location)}"))

    if spec.organizer:
        lines.extend(_format_organizer(spec.organizer))

    for att in spec.attendees:
        lines.extend(_format_attendee(att))

    for attch in spec.attachments:
        lines.extend(_format_attachment(attch))

    lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")

    # Join with CRLF per RFC 5545
    return "\r\n".join(lines) + "\r\n"


def parse_name_email(value: str) -> Tuple[str, str]:
    s = value.strip()
    if "<" in s and s.endswith(">"):
        name_part, email_part = s.split("<", 1)
        name = name_part.strip().strip('"')
        email = email_part[:-1].strip()
        return name, email
    if "@" in s and " " not in s:
        return s, s
    raise ValueError("Expected format 'Name <email@example.com>' or 'email@example.com'")


def parse_attendee(value: str) -> Attendee:
    parts = [p.strip() for p in value.split(";") if p.strip()]
    if not parts:
        raise ValueError("Empty attendee value")
    name_email = parts[0]
    name, email = parse_name_email(name_email)
    params = {"status": "NEEDS-ACTION", "role": "REQ-PARTICIPANT", "rsvp": "FALSE"}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().lower()] = v.strip()
    return Attendee(
        common_name=name,
        email=email,
        partstat=params.get("status", "NEEDS-ACTION"),
        role=params.get("role", "REQ-PARTICIPANT"),
        rsvp=params.get("rsvp", "FALSE"),
    )


def parse_attachment(value: str) -> AttachmentSpec:
    parts = [p.strip() for p in value.split(";") if p.strip()]
    if not parts:
        raise ValueError("Empty attachment value")
    path = parts[0]
    mime: Optional[str] = None
    label: Optional[str] = None
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            key = k.strip().lower()
            if key == "type":
                mime = v.strip()
            elif key == "label":
                label = v.strip()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Attachment not found: {path}")
    return AttachmentSpec(path=path, mime_type=mime, label=label)


def create_ics(
    summary: str,
    start_iso: str,
    end_iso: str,
    output_path: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    organizer_str: Optional[str] = None,
    attendees_values: Optional[List[str]] = None,
    attachment_values: Optional[List[str]] = None,
    uid: Optional[str] = None,
    prodid: str = "-//ics-spoofer//EN",
    method: str = "REQUEST",
) -> str:
    organizer: Optional[Organizer] = None
    if organizer_str:
        name, email = parse_name_email(organizer_str)
        organizer = Organizer(common_name=name, email=email)

    attendees = [parse_attendee(v) for v in (attendees_values or [])]
    attachments = [parse_attachment(v) for v in (attachment_values or [])]

    start_dt = _parse_iso_dt(start_iso)
    end_dt = _parse_iso_dt(end_iso)

    event_spec = EventSpec(
        summary=summary,
        description=description,
        location=location,
        start=start_dt,
        end=end_dt,
        organizer=organizer,
        attendees=attendees,
        attachments=attachments,
        uid=uid or str(uuid.uuid4()),
        prodid=prodid,
        method=method,
    )

    ics_text = build_ics(event_spec)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        # Note: we already used CRLF separators in content
        f.write(ics_text)
    return output_path