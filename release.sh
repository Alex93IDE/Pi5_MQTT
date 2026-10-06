#!/bin/bash
# Bump the version, commit and tag it. Usage: bash release.sh patch|minor|major
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$SCRIPT_DIR/pi5mqtt/__init__.py"
PART="$1"

if [[ "$PART" != "patch" && "$PART" != "minor" && "$PART" != "major" ]]; then
    echo "Usage: bash release.sh patch|minor|major"
    exit 1
fi

cd "$SCRIPT_DIR"

if [ -n "$(git status --porcelain)" ]; then
    echo "Working tree is not clean. Commit or stash your changes first."
    exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ]; then
    echo "You are on '$BRANCH'. Releases are made from main."
    exit 1
fi

CURRENT="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$VERSION_FILE")"
if [[ ! "$CURRENT" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Could not read version from $VERSION_FILE"
    exit 1
fi

IFS=. read -r MAJOR MINOR PATCH <<< "$CURRENT"
case "$PART" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
esac
NEW="$MAJOR.$MINOR.$PATCH"

if git rev-parse -q --verify "refs/tags/v$NEW" > /dev/null; then
    echo "Tag v$NEW already exists."
    exit 1
fi

echo "==> $CURRENT -> $NEW"
sed -i "s/^__version__ = \".*\"$/__version__ = \"$NEW\"/" "$VERSION_FILE"
git commit -q -m "$NEW" -- "$VERSION_FILE"
git tag -a "v$NEW" -m "$NEW"
echo "==> Created commit and tag v$NEW"

echo ""
read -r -p "Push to origin now? [y/N] " ANSWER
if [[ "$ANSWER" =~ ^[yY]$ ]]; then
    git push origin main
    git push origin "v$NEW"
else
    echo "Not pushed. When ready: git push origin main && git push origin v$NEW"
fi
