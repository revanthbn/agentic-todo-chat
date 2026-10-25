# AI Engineer take-home: agentic todo chat

**Time box:** 2 hours of work. Please stop when the time is up and submit what you have.  
**Format:** Git repository or zip.  
**Next step:** If selected, you will join one interview round: a live coding session where you extend this project with your AI assistant to show how you develop with agents.

## Why this exercise

We want to see how you build with an AI assistant: how you break down a task, choose a stack, prompt, check results, and handle an incomplete implementation. The development process matters as much as the demo.

## Build a small working slice

Create a chat interface for a todo list. A command-line interface is fine; a web UI is optional.

The chat should:

- Handle todo actions: add, list, update, complete, and delete. A partial implementation is acceptable if you identify what remains.
- Keep context across turns by default. For example, after “Add a task to send the quote,” the user can say “Change that to send the revised quote.”
- Ask for clarification when a reference could match more than one todo.
- Load skill instructions and tool definitions on demand. Start with a small catalog of names and descriptions; load the detailed instructions or schema only when a request needs them. Show which capability loaded in a log or trace.
- Validate an action before changing data and tell the user when an action fails.

Use any language, framework, model, and storage you can work with quickly. Explain **why** you chose them and one tradeoff. Local or in-memory storage is acceptable for the prototype. Tests may mock the model, but identify whether the demo uses a live model or a substitute.

## Show us your development process

Include a `PROCESS.md` with:

1. Your initial plan and what you chose to finish within two hours.
2. Important decisions and alternatives you considered, including your stack choice.
3. The checks you ran, what failed, and what you changed as a result.
4. What works, what does not, and what you would do next.
5. **Ideally, a prompt transcript:** a link to an exported AI-assistant conversation or 5–10 representative prompt-and-response excerpts in chronological order. Include the prompts you wrote, the useful or incorrect parts of the responses, and how you verified or revised them. Redact credentials and personal data. If you did not use an AI assistant, describe your development steps instead.

We are interested in your judgment, not the number of prompts or lines of code. You may use AI tools freely. Please be clear about what the tools produced and what you verified yourself.

## Production deployment note

In the README or a short `DEPLOYMENT.md`, explain how you would deploy **your** design in production. Name the hosting service and database you would choose, then cover:

- The path from chat request to model, selected tool, and todo storage.
- Authentication, user data isolation, secrets, and tool permissions.
- Deployment, database migration, and rollback.
- Monitoring for failed actions, latency, and model cost.
- The first likely scaling limit and what would prompt a change.

This is a plan, not a request to deploy the prototype.

## Submission checklist

- Source code and a README with one command to run the demo.
- `PROCESS.md`, including the prompt transcript or development steps.
- A short production deployment note.
- At least one reproducible multi-turn example and one check of on-demand loading. A test, script, or copyable transcript is enough.

We will review the working slice, the reasoning behind it, how you checked AI-generated work, and how honestly you describe gaps. A small, well-explained result is better than a larger demo that hides failures.
