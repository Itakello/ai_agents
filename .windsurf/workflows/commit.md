---
description: Automate the process of analyzing, grouping, and committing code changes with user-in-the-loop approval, following project best practices.
---

1. **Analyze Changes**
   - Run `git status` and `git diff` to detect all changes.
   - Group changes by logical concern (e.g., feature, bugfix, refactor, test, docs, etc.).
   - For each group, summarize the intent and affected files.

2. **Propose Commit Messages**
   - Suggest a short, clear commit message for each group (imperative, present tense).
   - Use conventional commit prefixes if appropriate (e.g., `feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
   - Optionally, provide a longer description if needed.

3. **User Approval**
   - Present the grouped changes and proposed commit messages to the user.
   - Allow the user to approve, edit, or reject each group/message.

4. **Commit**
   - For each approved group:
     - Stage the relevant files.
     - Commit with the approved message.
   - Optionally, prompt to push or open a PR.

## Notes
- Ensure each commit is focused and atomic.
- Reference issues or tickets in commit messages if relevant.
- Follow project and PEP 8 commit message guidelines.
- If changes cannot be separated cleanly, explain and seek user input.
