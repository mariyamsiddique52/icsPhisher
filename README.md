# ics-spoofer

Generate ICS calendar files with spoofed organizer/attendees, statuses, and embedded attachments.

## Install

From the repo root:

```bash
pip install -e .
```

Or run without install:

```bash
python -m ics_spoofer.cli --help
```

## Usage

```bash
ics-spoofer \
  --summary "Quarterly Review" \
  --description "Agenda attached." \
  --location "Board Room" \
  --start "2025-01-20T10:00:00Z" \
  --end "2025-01-20T11:00:00Z" \
  --organizer "Alice Admin <alice@example.com>" \
  --attendee "Bob Boss <bob@example.com>;status=ACCEPTED;role=REQ-PARTICIPANT;rsvp=FALSE" \
  --attendee "Carol <carol@example.com>;status=TENTATIVE" \
  --attach "./agenda.pdf;type=application/pdf;label=Agenda.pdf" \
  --output ./meeting.ics
```

- **Attendee spec**: `Name <email>;status=ACCEPTED;role=REQ-PARTICIPANT;rsvp=FALSE`
  - status: ACCEPTED|DECLINED|TENTATIVE|NEEDS-ACTION (default: NEEDS-ACTION)
  - role: REQ-PARTICIPANT|OPT-PARTICIPANT|NON-PARTICIPANT|CHAIR (default: REQ-PARTICIPANT)
  - rsvp: TRUE|FALSE (default: FALSE)
- **Attachment spec**: `/path/to/file;type=application/pdf;label=Agenda.pdf` (type optional; label optional)

The tool folds ICS lines per RFC 5545 and escapes special characters in text fields.
