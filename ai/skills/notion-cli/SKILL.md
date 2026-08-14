---
name: notion-cli
description: >-
  Use the Notion CLI (`ntn`) to authenticate, inspect and call the Notion API,
  read or modify pages, query data sources, upload and attach files, and
  scaffold, deploy, or manage Notion Workers. Use whenever a task mentions
  Notion CLI usage, the `ntn` command, Notion API requests, pages, databases,
  data sources, comments, file uploads, Workers, or terminal/CI automation
  against Notion.
---

# Notion CLI

Use `ntn` as the primary interface for authenticated Notion operations from a
terminal. Prefer the CLI's live help and generated endpoint documentation over
memorized syntax because the command surface and Notion API version evolve.

## Workflow

1. Classify the task as read-only API inspection, page/content editing, data
   source querying, file upload, or Worker management.
2. Check whether `ntn` is installed with `ntn --version`. If it is missing,
   choose an install method appropriate for the host OS and obtain approval
   before installing software.
3. Check authentication without exposing secrets. Prefer an existing
   `NOTION_API_TOKEN`; otherwise use the CLI login flow.
4. Inspect the live command or endpoint before constructing unfamiliar input.
5. Read the target first when making a change, confirm the workspace and target
   for remote writes, and avoid destructive operations unless explicitly
   requested.
6. Execute the smallest request that satisfies the task.
7. Verify the result with `get`, `list`, a follow-up API request, or a page read.

## Discover the Current Syntax

Run these before guessing a command, endpoint, method, or request schema:

```bash
ntn --help
ntn <command> --help
ntn api ls
ntn api <path> --help
ntn api <path> --docs
ntn api <path> --spec
ntn pages get <page-id>
```

Use `--spec` to understand the reduced OpenAPI schema and `--docs` for the
official endpoint reference. If an endpoint supports multiple methods, pass
`-X GET`, `-X POST`, `-X PATCH`, or the required method while inspecting it.

## Install and Authenticate

Install only when `ntn` is not already available. Current official options are:

```bash
# macOS/Linux
curl -fsSL https://ntn.dev | bash

# macOS/Linux/Windows with Node.js 22+ and npm 10+
npm install --global ntn

# Windows x64 in PowerShell or Command Prompt
winget install Notion.ntn
```

Verify with:

```bash
ntn --version
ntn doctor
```

Authentication rules:

- Check `NOTION_API_TOKEN` first. It takes precedence over keychain-based
  login and is the preferred choice for CI, scripts, and unattended work.
- Use `ntn login` for an interactive browser authorization flow. Use
  `ntn login --no-browser`, then `ntn login poll`, on a remote machine or
  container.
- Use `ntn logout` only when the user asks to clear the CLI session.
- Set `NOTION_WORKSPACE_ID` for a single command that must target a
  non-default workspace. Do not switch the default workspace merely to run one
  request.
- If the host has no usable keychain, `NOTION_KEYRING=0 ntn login` stores the
  token in a local file; treat that file as a secret.
- Never print, paste, commit, or place a token in a command log. Do not use
  `--unsafe-verbose`; normal `--verbose` redacts the authorization header.

For PowerShell, set a token only in the current process when needed:

```powershell
$env:NOTION_API_TOKEN = "ntn_xxx..."
ntn api v1/users/me
```

Use the workspace's secret manager for persistent or CI configuration.

## Make API Requests

`ntn api <path>` adds authentication and the Notion API version headers. A
leading slash is optional. Without a body it sends `GET`; when a body is
present it defaults to `POST`. Override the method with `-X`.

```bash
# GET with a query parameter (`==` means query string)
ntn api v1/users page_size==100

# POST with small inline body fields
ntn api v1/pages parent[page_id]=abc123

# POST with JSON body (`-d` and `--data` are equivalent)
ntn api v1/pages --data '{"parent":{"page_id":"abc123"}}'

# PATCH with a typed boolean (`:=` preserves JSON type)
ntn api v1/pages/abc123 -X PATCH archived:=true
```

Inline input syntax:

- `field=value` creates a string body field.
- `field:=json` parses a JSON boolean, number, string, array, object, or null.
- `name==value` adds a query parameter.
- `Header:Value` adds a request header.
- Use bracket or dot notation for nested objects; use explicit indexes or `[]`
  for arrays and repeated values.

```bash
ntn api v1/search query=roadmap page_size:=10

ntn api v1/pages \
  parent[page_id]="$PARENT_PAGE_ID" \
  properties[Name][title][0][text][content]="CLI-created page"

ntn api "v1/blocks/$PAGE_ID/children" -X PATCH \
  children[0][type]=paragraph \
  children[0][paragraph][rich_text][0][text][content]="First paragraph"
```

For larger or generated bodies, use exactly one body source: inline fields,
`--data`, or JSON from stdin. Query parameters and headers may still be added.

```bash
ntn api v1/search --data '{"query":"roadmap","page_size":10}'
cat create-page.json | ntn api v1/pages
```

Use `--notion-version` for one request or `NOTION_API_VERSION` for a shell or
script. Use `ntn --verbose api ...` to inspect the final method, URL, status,
and request ID while debugging; keep the output private.

## Pages, Markdown, and Comments

Prefer the page wrappers for Markdown content. The current CLI exposes
`ntn pages create` and `ntn pages edit`; check `ntn pages --help` because a
version may use a different edit/update spelling.

```bash
# Read page content as Markdown
ntn pages get <page-id>

# Create under a page, database, or data source
ntn pages create --parent page:<parent-id> --content "## Heading"

# Replace page content from Markdown
ntn pages edit <page-id> --content "## Updated heading"

# For multiline Markdown, omit --content and pipe a file
cat page.md | ntn pages create --parent page:<parent-id>
cat page.md | ntn pages edit <page-id>
```

For comments, use the `markdown` field with `ntn api`:

```bash
ntn api v1/comments --data '{
  "parent":{"page_id":"abc123"},
  "markdown":"Here is a [link](https://example.com) and **bold text**."
}'
```

Use Markdown for ordinary formatting such as bold, italic, code, links, and
headings. Fall back to the API's `rich_text` shape only for features Markdown
cannot express, such as mentions, custom emoji, or colors. After a write,
retrieve the page or relevant block to verify the content.

For data-source work, prefer the dedicated commands when available:

```bash
ntn datasources query <data-source-id>
ntn datasources resolve <database-id>
```

Use `ntn api` when the dedicated command does not expose the required option.

## File Uploads

Use `ntn files` for the normal File Uploads lifecycle. It creates the upload,
sends bytes, completes it, and returns an upload ID; it does not attach the
file to a page automatically.

```bash
ntn files create < image.png
ntn files create --external-url https://example.com/photo.png
ntn files list
ntn files get <upload-id>
```

Use `--filename` and `--content-type` when stdin does not preserve reliable
metadata. Use `--json` for a machine-readable object or `--plain` for
tab-separated scripting output. External URL imports are asynchronous; poll
`ntn files get <upload-id>` until the status is `uploaded` or `failed`.

Attach an uploaded file with a `file_upload` object through `ntn api`, for
example as an image block:

```bash
ntn api "v1/blocks/$PAGE_ID/children" -X PATCH \
  children[0][type]=image \
  children[0][image][type]=file_upload \
  children[0][image][file_upload][id]="$FILE_UPLOAD_ID"
```

Attach uploads before their expiry time (normally about one hour). If more
control is required, inspect `ntn api --help` for the multipart `--file`
option. Do not upload sensitive files or public URLs without explicit user
authorization.

## Notion Workers

Workers are small TypeScript/Node programs hosted by Notion. Use the CLI to
scaffold, deploy, inspect, execute, and manage them:

```bash
ntn workers new my-worker
cd my-worker
ntn workers deploy
ntn workers list                 # `ls` is an alias
ntn workers get <worker-id>
ntn workers exec <capability-key>
ntn workers capabilities list
ntn workers runs list
ntn workers runs logs <run-id>
```

`ntn workers deploy` creates a Worker when `workers.json` is absent and updates
the configured Worker otherwise. Resolve the target from `--worker-id` or the
local `workers.json`; inspect that file before deploying. Use `--json` or
`--plain` for scripts.

Manage Worker configuration only when requested:

```bash
ntn workers env set KEY=value
ntn workers env list
ntn workers env pull
ntn workers env push
ntn workers sync status <capability-key>
ntn workers sync trigger <capability-key>
```

Treat `deploy`, `env push`, `sync trigger`, `workers delete`, and any operation
against a production workspace as remote side effects. Confirm the intended
workspace, Worker, and scope before running them, and verify the resulting
deployment or run afterward.

## Troubleshooting

- Unexpected `POST`: a body came from inline fields, `--data`, or stdin. Use
  `-X` to select the intended method.
- Wrong inline type: use `:=` for JSON values and `=` only for strings.
- Ambiguous `--help`, `--docs`, or `--spec`: pass the intended `-X METHOD`.
- Conflicting body input: use only one of inline fields, `--data`, or stdin.
- Authentication or keychain failure: run `ntn doctor`; for unattended jobs,
  use a secret-backed `NOTION_API_TOKEN`.
- File remains pending: poll `ntn files get`, then check the URL, MIME type,
  size, and expiry before retrying.
- Worker command cannot find its target: pass `--worker-id` or inspect the
  `workerId` in `workers.json`.

## Authoritative References

- [Notion CLI overview](https://developers.notion.com/cli/get-started/overview)
- [API requests](https://developers.notion.com/cli/guides/api-requests)
- [File uploads](https://developers.notion.com/cli/guides/file-uploads)
- [Command reference](https://developers.notion.com/cli/reference/commands)
- [Source skill](https://github.com/makenotion/skills/tree/main/skills/notion-cli)
