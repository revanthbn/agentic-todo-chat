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
      candidate_ids:
        type: array
        items: {type: integer}
        description: Every todo id from the list that could plausibly be meant (by meaning, not just exact words); empty if none.
    required: [target]
---
`target` is the user's own words for the todo. Copy them; do not expand,
correct or guess. If they say "that" or "it", use exactly "that" or "it".
`candidate_ids` lists EVERY todo from the current list that could plausibly be
meant, including matches by meaning ("shopping" → "buy milk", "buy tofu").
Do not narrow down to one when several fit: the application asks the user.
Leave it empty for "that"/"it" or when nothing fits.
