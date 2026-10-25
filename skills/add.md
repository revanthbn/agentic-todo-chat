---
tool:
  name: add_todo
  description: Create a new todo.
  parameters:
    type: object
    properties:
      text:
        type: string
        description: The todo text, written as a short task (e.g. "send the quote").
    required: [text]
---
Extract the task the user wants to add. Drop filler like "add a task to",
"remind me to", "please". Keep the user's wording for the task itself.
Do not invent details.
