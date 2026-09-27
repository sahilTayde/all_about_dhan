#!/bin/sh
# Shared matcher for Mac hooks. POSIX / macOS /bin/sh.
# Patterns live in scripts/mac/protected_paths.txt.

protected_list() {
  root=$(git rev-parse --show-toplevel)
  printf '%s\n' "$root/scripts/mac/protected_paths.txt"
}

# Return 0 if $1 matches glob $2. Supports exact, trailing /**, and * / ?.
path_matches() {
  path=$1
  pat=$2
  case $pat in
    *'/**')
      prefix=${pat%/**}
      if [ "$path" = "$prefix" ]; then
        return 0
      fi
      case $path in
        "$prefix"/*) return 0 ;;
      esac
      return 1
      ;;
    *'*'*|*'?'*)
      case $path in
        $pat) return 0 ;;
      esac
      return 1
      ;;
    *)
      [ "$path" = "$pat" ]
      ;;
  esac
}

is_protected() {
  path=$1
  list=$(protected_list)
  [ -f "$list" ] || return 1
  while IFS= read -r pat || [ -n "$pat" ]; do
    case $pat in
      ''|\#*) continue ;;
    esac
    if path_matches "$path" "$pat"; then
      return 0
    fi
  done < "$list"
  return 1
}

# Print staged paths, including deletes and both sides of a rename/copy.
# git name-status: M|A|D<TAB>path  or  R100<TAB>old<TAB>new
staged_paths() {
  git diff --cached --name-status | while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    status=${line%%	*}
    rest=${line#*	}
    case $status in
      R*|C*)
        old=${rest%%	*}
        new=${rest#*	}
        printf '%s\n' "$old" "$new"
        ;;
      *)
        printf '%s\n' "$rest"
        ;;
    esac
  done
}

protected_hits() {
  staged_paths | while IFS= read -r path || [ -n "$path" ]; do
    [ -n "$path" ] || continue
    if is_protected "$path"; then
      printf '%s\n' "$path"
    fi
  done
}
