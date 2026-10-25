---
tool:
  name: delete_todo
  description: Remove an existing todo.
  parameters:
    type: object
    properties:
      target:
        type: string
        description: The user's own words for which todo to delete, copied as-is (e.g. "the quote", "that").
    required: [target]
---
`target` is the user's own words for the todo. Copy them; do not expand,
correct, or guess which todo they mean. If they say "that" or "it", use
exactly "that" or "it". The application decides which todo matches.
