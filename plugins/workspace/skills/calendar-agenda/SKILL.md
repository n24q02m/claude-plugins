---
name: calendar-agenda
description: Daily agenda review, upcoming meeting briefing, attendee prep, and scheduling conflict detection
argument-hint: "[date or time range, e.g. today, tomorrow, this-week]"
---

# Calendar Agenda

Systematic daily schedule review and briefing for Google Workspace calendar events.

## Workflow

1. **Fetch Events**: Call `calendar(action="list_events", timeMin="...", timeMax="...")` for the specified time window.
2. **Conflict Detection**: Check for overlapping time spans between confirmed events.
3. **Attendee & Context Briefing**: For each meeting with external attendees or video links, highlight:
   - Meeting title and organizer
   - Time span and duration
   - Hangouts/Meet URL
   - Key attendees
4. **Summary & Preparation**: Flag back-to-back blocks without breaks and identify events missing descriptions or locations.

## When to Use

- Morning briefing ("What's on my schedule today?")
- Preparing for upcoming meetings
- Identifying schedule conflicts
