---
tool:
  name: update_todo
  description: Change the text of an existing todo.
  parameters:
    type: object
    properties:
      target:
        type: string
        description: The user's own words for which todo to change, copied as-is (e.g. "the quote", "that", "it").
      text:
        type: string
        description: The new todo text.
    required: [target, text]
---
`target` is the user's own words for the todo. Copy them; do not expand,
correct, or guess which todo they mean. If they say "that" or "it", use
exactly "that" or "it". The application decides which todo matches.
`text` is the full new text of the todo.
