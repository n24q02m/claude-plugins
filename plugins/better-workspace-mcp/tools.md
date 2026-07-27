# Better Workspace MCP -- Tools Reference

better-workspace-mcp exposes Google Workspace through 11 composite tools driven by an `action` parameter, plus `config` (credential and account management) and `help`. That is the N+2 layout every server in this stack follows: one tool per domain, never one tool per API call.

Every domain tool also accepts `account` -- the email address of the Google account the call should act as. Omit it and the call runs against the primary account. Naming an account that is not configured is an error that says so; the call is never quietly rerouted to the primary, because a silent fallback would act on the wrong mailbox or drive.

`time`, `config`, and `help` need no Google account and answer before any consent has happened. `time` is the quickest check that the server is wired up at all.

## docs

Google Docs.

| Action | Purpose | Key parameters |
|---|---|---|
| `getText` | Read document text | `documentId` (required), `tabId` |
| `create` | Create a document | `title` (required), `content` |
| `writeText` | Insert text | `documentId`, `text` (required); `position`, `tabId` |
| `getSuggestions` | List pending suggestions | `documentId` (required) |
| `replaceText` | Find and replace | `documentId`, `findText`, `replaceText` (required); `tabId` |
| `formatText` | Apply formatting ranges | `documentId`, `formats` (required); `tabId` |

`position` accepts `"beginning"`, `"end"` (default), or a positive integer index.

## drive

Files and folders.

| Action | Purpose | Key parameters |
|---|---|---|
| `search` | Search files | `query` |
| `findFolder` | Locate a folder by name | `folderName` |
| `createFolder` | Create a folder | `name`; `parentId` |
| `moveFile` | Move a file | `fileId`, `destinationFolderId` |
| `renameFile` | Rename a file | `fileId`, `newName` |
| `trashFile` | Send a file to trash | `fileId` |
| `downloadFile` | Download file content | `fileId` |
| `getComments` | Read file comments | `fileId` |

## calendar

Events across calendars.

| Action | Purpose | Key parameters |
|---|---|---|
| `listCalendars` | List available calendars | -- |
| `listEvents` | List events | `calendarId`, `start`, `end` |
| `getEvent` | Read one event | `calendarId`, `eventId` |
| `createEvent` | Create an event | `summary`, `start`, `end`; `description`, `attendees` |
| `updateEvent` | Modify an event | `calendarId`, `eventId` + fields to change |
| `deleteEvent` | Delete an event | `calendarId`, `eventId` |
| `respondToEvent` | Accept / decline an invite | `calendarId`, `eventId` |
| `findFreeTime` | Find open slots | `start`, `end` |

## gmail

Mail.

| Action | Purpose | Key parameters |
|---|---|---|
| `search` | Search messages | `query` |
| `get` | Read one message | `messageId` |
| `send` | Send a message | `to`, `subject`, `body` |
| `createDraft` | Save a draft | `to`, `subject`, `body` |
| `sendDraft` | Send an existing draft | `draftId` |
| `modify` | Change labels on a message | `messageId`, `labelIds` |
| `batchModify` | Change labels on many messages | `labelIds` |
| `modifyThread` | Change labels on a thread | `threadId`, `labelIds` |
| `downloadAttachment` | Download an attachment | `messageId` |
| `listLabels` | List labels | -- |
| `createLabel` | Create a label | `name` |

## sheets

Spreadsheets, read-only.

| Action | Purpose | Key parameters |
|---|---|---|
| `getText` | Read the sheet as text | `spreadsheetId` |
| `getRange` | Read a specific range | `spreadsheetId`, `range` |
| `getMetadata` | Sheet names, sizes, properties | `spreadsheetId` |

Writing to a spreadsheet is not exposed.

## slides

Presentations -- 19 actions covering slides, text, shapes, images, tables, and speaker notes.

| Group | Actions |
|---|---|
| Read | `getText`, `getMetadata`, `getImages`, `getSpeakerNotes`, `getSlideThumbnail` |
| Deck structure | `create`, `addSlide`, `deleteSlide`, `duplicateSlide`, `reorderSlides` |
| Text | `insertText`, `deleteText`, `replaceAllText`, `updateSpeakerNotes`, `updateTextStyle` |
| Objects | `addShape`, `addImage`, `addTable`, `updateShapeProperties` |

Common parameters: `presentationId`, `slideId`, `title`, `text`.

## tasks

Task lists and tasks.

| Action | Purpose | Key parameters |
|---|---|---|
| `listTaskLists` | List task lists | -- |
| `listTasks` | List tasks in a list | `taskListId` |
| `createTask` | Create a task | `taskListId`, `title`; `notes`, `due` |
| `updateTask` | Modify a task | `taskListId`, `taskId` + fields to change |
| `completeTask` | Mark a task done | `taskListId`, `taskId` |
| `deleteTask` | Delete a task | `taskListId`, `taskId` |

## chat

Google Chat.

| Action | Purpose | Key parameters |
|---|---|---|
| `listSpaces` | List spaces | -- |
| `findSpaceByName` | Locate a space by display name | `displayName` |
| `setUpSpace` | Create or find a space | `displayName` |
| `getMessages` | Read messages in a space | `spaceId` |
| `listThreads` | List threads in a space | `spaceId` |
| `sendMessage` | Post to a space | `spaceId`, `text`; `threadId` |
| `sendDm` | Direct-message a person | `email`, `text` |
| `findDmByEmail` | Locate an existing DM | `email` |

## people

Profile lookups.

| Action | Purpose | Key parameters |
|---|---|---|
| `getMe` | The authenticated user's profile | -- |
| `getUserProfile` | Another person's profile | `resourceName` |
| `getUserRelations` | Relations on a profile | `resourceName` |

## forms

Forms.

| Action | Purpose | Key parameters |
|---|---|---|
| `create` | Create a form | `title`; `documentTitle` |
| `get` | Read a form's structure | `formId` |
| `batchUpdate` | Add or change questions | `formId`, `requests` |
| `listResponses` | List submitted responses | `formId`; `pageSize`, `pageToken`, `filter` |
| `getResponse` | Read one response | `formId`, `responseId` |

Three things about Forms that are easy to get wrong:

- Questions are added with `batchUpdate`, not at `create`. A `create` call takes only the title.
- Responses are read-only. The Forms API cannot write one, so there is no `createResponse`.
- Listing or deleting forms goes through `drive`, not here.

`formId` also accepts the editor URL `https://docs.google.com/forms/d/<formId>/edit`.

## time

Local date, time, and timezone helpers. No Google account needed.

| Action | Purpose |
|---|---|
| `getCurrentDate` | Today's date |
| `getCurrentTime` | Current time |
| `getTimeZone` | The local timezone |

## config

Credential state and account management.

| Action | Purpose | Key parameters |
|---|---|---|
| `status` | Credential state and the account being acted as | -- |
| `setup_start` | Return the setup URL | `force` (restart setup) |
| `setup_reset` | Wipe saved credentials | -- |
| `setup_complete` | Re-check state after consent | -- |
| `account_add` | Return a URL that adds one more account once consent completes | -- |
| `account_list` | Configured accounts and which is primary | -- |
| `account_remove` | Forget one account | `account` (required) |
| `account_set_default` | Make one account primary | `account` (required) |
| `set` | Set a runtime setting | `key`, `value` |
| `cache_clear` | Clear cached client state | -- |

The first account authorized becomes the primary. Removing the primary promotes one of the remaining accounts; removing the last one puts the server back to `awaiting_setup`. Adding an account never changes which one is primary -- use `account_set_default` for that.

In HTTP mode, `account_add` completes through the server's `/accounts/callback`, so the OAuth client has to be a Web application type with that redirect URI registered. See [setup](/servers/better-workspace-mcp/setup/).

## help

Full documentation for one tool.

| Parameter | Values |
|---|---|
| `tool_name` | `docs` \| `drive` \| `calendar` \| `gmail` \| `sheets` \| `slides` \| `tasks` \| `chat` \| `people` \| `forms` \| `time` \| `config` \| `help` |
