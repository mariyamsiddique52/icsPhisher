import argparse
import sys
from typing import List

from .core import create_ics


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ics-spoofer",
        description="Generate ICS files with spoofed organizer/attendees, statuses, and attachments",
    )
    p.add_argument("--output", required=True, help="Output .ics file path")
    p.add_argument("--summary", required=True, help="Event title")
    p.add_argument("--start", required=True, help="Start datetime (ISO 8601, e.g., 2025-01-20T10:00:00Z)")
    p.add_argument("--end", required=True, help="End datetime (ISO 8601)")
    p.add_argument("--description", help="Event description (message body)")
    p.add_argument("--location", help="Event location")
    p.add_argument("--organizer", help="Organizer as 'Name <email@example.com>'")
    p.add_argument(
        "--attendee",
        action="append",
        dest="attendees",
        help="Attendee spec 'Name <email>;status=ACCEPTED;role=REQ-PARTICIPANT;rsvp=FALSE' (repeatable)",
    )
    p.add_argument(
        "--attach",
        action="append",
        dest="attachments",
        help="Attachment spec '/path;type=application/pdf;label=Label' (repeatable)",
    )
    p.add_argument("--uid", help="Custom UID for the event")
    p.add_argument("--prodid", default="-//ics-spoofer//EN", help="PRODID string")
    p.add_argument("--method", default="REQUEST", help="METHOD (REQUEST, PUBLISH, CANCEL)")
    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        create_ics(
            summary=args.summary,
            start_iso=args.start,
            end_iso=args.end,
            output_path=args.output,
            description=args.description,
            location=args.location,
            organizer_str=args.organizer,
            attendees_values=args.attendees,
            attachment_values=args.attachments,
            uid=args.uid,
            prodid=args.prodid,
            method=args.method,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())