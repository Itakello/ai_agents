---
description: Automate the process of analyzing, grouping, and committing code changes with user-in-the-loop approval, following project best practices.
---

1. **Analyze Changes**
   - Run `git status` and `git diff` to detect all changes.
   - Group changes by logical concern (e.g., feature, bugfix, refactor, test, docs, etc.).
   - Summarize the intent and affected files for all groups.

2. **Propose Commit Message**
   - Suggest a comprehensive, clear commit message summarizing all changes (imperative, present tense).
   - Use conventional commit prefixes if appropriate (e.g., `feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
   - Optionally, provide a longer description if needed.

3. **User Approval**
   - Present the grouped changes and proposed commit message to the user.
   - Allow the user to approve, edit, or reject the message.

4. **Commit**
   - If approved, stage all files and commit with the approved message.
   - Optionally, prompt to push or open a PR.

## Notes
- Reference issues or tickets in the commit message if relevant.
- Follow project and PEP 8 commit message guidelines.
- If changes cannot be separated cleanly, explain and seek user input.
