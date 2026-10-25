---
tool:
  name: complete_todo
  description: Mark an existing todo as done.
  parameters:
    type: object
    properties:
      target:
        type: string
        description: The user's own words for which todo to complete, copied as-is (e.g. "call", "that").
    required: [target]
---
`target` is the user's own words for the todo. Copy them; do not expand,
correct, or guess which todo they mean. If they say "that" or "it", use
exactly "that" or "it". The application decides which todo matches.
