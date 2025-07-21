# Step-by-Step Git Push Instructions

## Current Status
- You're on the `main` branch
- You have 1 unpushed commit (Node.js 20 Alpine upgrade - already committed)
- You have new files and modifications for the markdown formatting feature
- Next.js is already at version 15.3.3 (latest stable)
- Temporary test files are now in .gitignore

## Step 1: Create and Switch to Feature Branch

```bash
# Create a new feature branch for the markdown formatting improvements
git checkout -b feature/lawyer-chat-markdown-formatting

# This creates and switches to the new branch
```

## Step 2: Add Your Changes

```bash
# Add the new markdown formatter file
git add services/lawyer-chat/src/utils/markdownFormatter.ts

# Add the modified textFilters file
git add services/lawyer-chat/src/utils/textFilters.ts

# Add the test file (optional, but recommended)
git add services/lawyer-chat/src/utils/__tests__/markdownFormatter.test.ts

# Add documentation files
git add services/lawyer-chat/MARKDOWN_FORMATTING_IMPROVEMENTS.md
git add services/lawyer-chat/FORMATTING_VERIFICATION.md

# Note: Don't add the test files in the root directory (test-formatter.mjs, etc.)
# as they're just temporary test files
```

## Step 3: Commit Your Changes

```bash
# Create a descriptive commit message
git commit -m "feat: Add comprehensive markdown formatting for lawyer-chat responses

- Implement automatic header detection and formatting (##, ###)
- Add mathematical expression formatting with code blocks
- Standardize bullet lists to markdown format
- Ensure consistent spacing between sections
- Add automatic emphasis for key scientific terms
- Integrate formatter into existing text processing pipeline"
```

## Step 4: Push to Feature Branch

```bash
# Push the feature branch to remote
git push -u origin feature/lawyer-chat-markdown-formatting

# The -u flag sets up tracking between local and remote branch
```

## Step 5: Create Pull Request (Recommended)

After pushing to the feature branch, you should:
1. Go to your GitHub repository
2. You'll see a prompt to create a Pull Request
3. Create PR from `feature/lawyer-chat-markdown-formatting` to `main`
4. Add description of changes
5. Review and merge

## Step 6: Push to Main Branch (Alternative - Direct Push)

If you want to push directly to main instead:

```bash
# First, switch back to main
git checkout main

# Merge your feature branch
git merge feature/lawyer-chat-markdown-formatting

# Push to main
git push origin main
```

## Complete Command Sequence (Simplified)

Here's the complete sequence to run:

```bash
# 0. First, push the existing commit on main (Node.js 20 Alpine upgrade)
git push origin main

# 1. Create feature branch from updated main
git checkout -b feature/lawyer-chat-markdown-formatting

# 2. Add ALL changes at once (safe now - temp files are in .gitignore)
git add -A

# 3. Check what will be committed (recommended)
git status

# 4. Commit with comprehensive message
git commit -m "feat: Add comprehensive markdown formatting for lawyer-chat responses

- Implement automatic header detection and formatting (##, ###)
- Add mathematical expression formatting with code blocks
- Standardize bullet lists to markdown format
- Ensure consistent spacing between sections
- Add automatic emphasis for key scientific terms
- Integrate formatter into existing text processing pipeline
- Works with Next.js 15.3.3 and Node.js 20 Alpine setup
- Add temporary test files to .gitignore"

# 5. Push feature branch
git push -u origin feature/lawyer-chat-markdown-formatting

# 6. Switch to main and merge
git checkout main
git merge feature/lawyer-chat-markdown-formatting
git push origin main
```

## One-Line Version (After First Push)

```bash
# Quick version after pushing existing commit:
git checkout -b feature/lawyer-chat-markdown-formatting && git add -A && git commit -m "feat: Add comprehensive markdown formatting for lawyer-chat responses" && git push -u origin feature/lawyer-chat-markdown-formatting
```

## Additional Notes

1. **Feature Branch Benefits**:
   - Allows code review via Pull Request
   - Keeps main branch stable
   - Easy to revert if needed
   - Better collaboration with team

2. **Before Pushing**:
   - Make sure all tests pass (or document known test issues)
   - Review your changes with `git diff`
   - Ensure no sensitive data is included

3. **After Pushing**:
   - Create Pull Request on GitHub
   - Document the changes in PR description
   - Request review if working with a team

## Troubleshooting

If you encounter conflicts or issues:

```bash
# Check remote status
git remote -v

# Fetch latest changes
git fetch origin

# If there are conflicts during merge
git status  # See conflicted files
# Resolve conflicts manually, then:
git add <resolved-files>
git commit

# If you need to undo changes
git reset --hard HEAD~1  # Undo last commit
git checkout -- <file>   # Discard changes to a file
```