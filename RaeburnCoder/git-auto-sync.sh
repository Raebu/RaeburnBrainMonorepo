#!/bin/bash

# Change to your project directory
cd "C:/Users/Martin Raeburn/Downloads/AI_Auto_Developer" || exit

# Fetch latest updates from GitHub to prevent conflicts
echo "Fetching latest updates..."
git pull origin main --rebase

# Check if there are any changes
if [[ -n $(git status --porcelain) ]]; then
    echo "Changes detected! Syncing with GitHub..."

    # Stage all changes
    git add .

    # Commit changes with a timestamp
    git commit -m "Auto-sync: $(date)"

    # Push changes to GitHub
    git push origin main

    echo "✅ Auto-sync complete!"
else
    echo "✅ No changes detected. Nothing to sync."
fi
