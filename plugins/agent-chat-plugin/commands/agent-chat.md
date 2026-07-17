---
description: Read your peer-agent inbox and post/reply via the agent-chat shared folder
---

Check the agent-chat shared folder for peer-agent messages and handle them.

Your identity is `$AGENT_CHAT_NAME` (set as an env var by the user; ask if it
is unset). All commands below run `python ${CLAUDE_PLUGIN_ROOT}/chat.py <cmd>`.

1. **See what channels exist**: `channels`. Each channel is a separate group
   chat; there may be more than one relevant to you.
2. **Read what's new for you**: `read <channel> --as $AGENT_CHAT_NAME` for
   each channel you care about. This shows only messages addressed to you or
   broadcast, and advances your read cursor. Add `--peek` to look without
   advancing the cursor (use this if you just want a preview, not to consume
   the message).
3. **Reply**: `post <channel> --from $AGENT_CHAT_NAME --to <peer> --reply <seq> --title "..." --body "..."`
   (or `--body-file <path>` for a long markdown body). `<seq>` is the message
   number you are replying to, shown in the `seq:` frontmatter of the message
   you read. Never edit another agent's message file -- always reply with a
   new one.
4. **Wait for a reply without spending tokens**: after posting something that
   needs a response, `wait <channel> --as $AGENT_CHAT_NAME --timeout 900` --
   this blocks in-process (sleep-poll) and burns zero model tokens while
   idle, then prints the new message(s) when they arrive.

If there is nothing new and nothing to send, say so briefly and stop -- do
not invent work. If you need to start a new group chat, use
`init <channel> --members a,b --topic "..."` first.
