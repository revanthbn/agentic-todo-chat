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
      candidate_ids:
        type: array
        items: {type: integer}
        description: Every todo id from the list that could plausibly be meant (by meaning, not just exact words); empty if none.
    required: [target, text]
---
`target` is the user's own words for the todo. Copy them; do not expand,
correct or guess. If they say "that" or "it", use exactly "that" or "it".
`candidate_ids` lists EVERY todo from the current list that could plausibly be
meant, including matches by meaning ("shopping" → "buy milk", "buy tofu").
Do not narrow down to one when several fit: the application asks the user.
Leave it empty for "that"/"it" or when nothing fits.
`text` is the full new text of the todo.
