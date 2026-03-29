# Discord room binding (v1)

Use this reference when the user wants a project agent bound to an existing Discord room.

## Goal

Bind one existing Discord room to one OpenClaw agent in a way that is explicit, reviewable, and easy to validate.

## Use this pattern

For a room-specific binding, combine:

1. a Discord guild/channel allowlist entry
2. a top-level route binding for the room

This is more precise than `openclaw agents bind`, which is better suited to channel/account-level routing.

## Required inputs

- `agentId`
- `discordGuildId`
- `discordChannelId`
- optional `discordAccountId` (default `default`)
- `discordMode` = `prepare` or `apply`

## Patch shape

Use a merge-safe config patch equivalent to this JSON5 structure:

```json5
{
  bindings: [
    {
      agentId: "<agentId>",
      match: {
        channel: "discord",
        accountId: "<discordAccountId>",
        peer: { kind: "channel", id: "<discordChannelId>" },
      },
    },
  ],
  channels: {
    discord: {
      groupPolicy: "allowlist",
      guilds: {
        "<discordGuildId>": {
          channels: {
            "<discordChannelId>": {
              allow: true,
              requireMention: false,
            },
          },
        },
      },
    },
  },
}
```

## Rules

- Preserve existing guild entries.
- Preserve existing channel entries.
- Preserve unrelated bindings.
- Deduplicate exact duplicates.
- If the same `peer.kind=channel` + `peer.id=<discordChannelId>` is already bound to another agent, stop and ask.
- If guild-level `users` or `roles` restrictions already exist, preserve them. Do not silently widen access.
- If the user prefers mention-gated behavior, set `requireMention: true` instead of `false`.

## Prepare mode

When `discordMode=prepare`:

- do not write config
- show the intended binding target
- show the intended allowlist target
- report whether the patch appears conflict-free or blocked by an existing route

## Apply mode

Before patching:

- inspect the relevant config/schema paths
- inspect current bindings and current Discord guild/channel config

When patching:

- use `gateway config.patch`
- include a human-readable `note`
- remember that the patch triggers a restart automatically

## Validation after apply

Check all of these:

- the room route exists for the intended `agentId`
- the guild entry exists
- the channel entry exists
- the channel entry allows traffic
- the final status is `applied`

## Failure cases

Mark the Discord portion `FAIL` when:

- required ids are missing
- the room is already owned by another agent
- the patch fails validation
- the post-patch config does not contain the expected route and allowlist entries
