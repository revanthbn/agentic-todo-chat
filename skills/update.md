---
tool:
  name: update_todo
  description: Change the text of an existing todo.
  parameters:
    type: object
    properties:
      target:
        type: string
        description: The shortest phrase naming the todo (e.g. "milk and eggs"), not the whole sentence. Use exactly "that" or "it" if the user did.
      text:
        type: string
        description: The new todo text.
      candidate_ids:
        type: array
        items: {type: integer}
        description: Every todo id from the list that could plausibly be meant, including paraphrases, other tenses and typos; empty if none.
    required: [target, text]
---
`target` is the shortest phrase that names the todo, not the whole sentence:
"i already bought milk anfd eggs" → "milk anfd eggs". If the user says "that" or
"it", use exactly "that" or "it".

`candidate_ids` lists every todo from the current list that could plausibly be
meant: paraphrases ("the shopping" → "buy milk", "buy tofu"), other tenses
("bought" → "buy") and typos ("anfd" → "and"). If several fit, include them all;
don't pick one. Leave it empty for "that"/"it" or when nothing fits. The
application makes the final decision and asks the user when it's unclear.

`text` is the full new text of the todo.
