#!/bin/sh
# Bootstrap a project's AI harness without cloning this repository.
#
#     curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh
#     curl -fsSL https://raw.githubusercontent.com/dougmotshell/harness-bootstrap/main/install.sh | sh -s -- ../my-project --dry-run
#
# The first argument is the target project (default: the current directory); every
# other argument goes straight to `scripts/init-project.py`, so `--dry-run`,
# `--check`, `--project` and friends all work through the pipe.
#
# The repository is fetched as a tarball into a temporary directory and removed on
# exit: nothing is left behind but the harness written into the target. Set
# HARNESS_BOOTSTRAP_REF to install from a branch, tag or commit other than `main`.
set -eu

REPO=${HARNESS_BOOTSTRAP_REPO:-dougmotshell/harness-bootstrap}
REF=${HARNESS_BOOTSTRAP_REF:-main}

die() {
	echo "install.sh: $*" >&2
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

# No mkdir: the bootstrap refuses a target that does not exist, on purpose — a typo in
# the path must not become a directory with a harness in it.
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

[ -f "$tmp/scripts/init-project.py" ] || die "tarball has no scripts/init-project.py — is $REF a valid ref?"

echo "harness-bootstrap: bootstrapping $target"
# No `exec`: the EXIT trap must still fire to remove the temporary checkout.
python3 "$tmp/scripts/init-project.py" "$target" "$@"
