---
tool:
  name: list_todos
  description: List todos.
  parameters:
    type: object
    properties:
      status:
        type: string
        enum: [all, open, done]
        description: Which todos to show. Default all.
    required: [status]
---
Use "open" if the user asks what is left/remaining/pending, "done" if they ask
what is finished/completed, otherwise "all".
