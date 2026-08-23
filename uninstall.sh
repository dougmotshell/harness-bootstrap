#!/bin/sh
# Remove the AI harness from a project, without cloning this repository.
#
#     curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/uninstall.sh | sh -s -- --dry-run
#     curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/uninstall.sh | sh
#
# Same shape as install.sh: the first argument is the target project (default: the
# current directory), every other argument goes to `scripts/uninstall-project.py`.
# Start with `--dry-run` — this is the direction that deletes files.
#
# Only what the bootstrap wrote comes out: merged files have their harness block,
# keys or import line removed, and a file the project changed afterwards is kept
# unless you pass --force.
set -eu

REPO=${HARNESS_BOOTSTRAP_REPO:-dougmotshell/harness-bootstrap}
REF=${HARNESS_BOOTSTRAP_REF:-main}

die() {
	echo "uninstall.sh: $*" >&2
	exit 1
}

have() {
	command -v "$1" >/dev/null 2>&1
}

target=.
if [ $# -gt 0 ]; then
	case $1 in
	-*) ;;
	*)
		target=$1
		shift
		;;
	esac
fi

have python3 || die "python3 is required"
have tar || die "tar is required"
[ -d "$target" ] || die "$target is not an existing directory"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/harness-bootstrap.XXXXXX")
trap 'rm -rf "$tmp"' EXIT INT TERM

url="https://codeload.github.com/$REPO/tar.gz/$REF"
echo "harness-bootstrap: fetching $REPO@$REF"
if have curl; then
	curl -fsSL "$url" | tar -xzf - --strip-components=1 -C "$tmp"
elif have wget; then
	wget -qO- "$url" | tar -xzf - --strip-components=1 -C "$tmp"
else
	die "curl or wget is required"
fi

[ -f "$tmp/scripts/uninstall-project.py" ] || die "tarball has no scripts/uninstall-project.py — is $REF a valid ref?"

echo "harness-bootstrap: cleaning $target"
# No `exec`: the EXIT trap must still fire to remove the temporary checkout.
python3 "$tmp/scripts/uninstall-project.py" "$target" "$@"
