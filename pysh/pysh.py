import json
import os
import time

print("Welcome to pysh ")

FS_FILE = "fs.json"

# load or create FS
if os.path.exists(FS_FILE):
    with open(FS_FILE, "r") as f:
        fs = json.load(f)
else:
    fs = {
        "pysh": {
            "root": {},
            "home": {}
        }
    }

current_path = ["pysh"]

# ── NEW STATE ──────────────────────────────────────────────
history    = []          # list of command strings
aliases    = {}          # alias name → command string
env        = {           # environment variables
    "USER": "root",
    "SHELL": "pysh",
    "HOME": "/pysh/home",
}
# ──────────────────────────────────────────────────────────


def save_fs():
    with open(FS_FILE, "w") as f:
        json.dump(fs, f, indent=4)


def get_dir(path):
    temp = fs
    for p in path:
        temp = temp[p]
    return temp


def resolve_path(path_str):
    path = current_path.copy()
    parts = path_str.split("/")
    for p in parts:
        if p == "" or p == ".":
            continue
        elif p == "..":
            if len(path) > 1:
                path.pop()
        else:
            path.append(p)
    return path


def expand_vars(text):
    """Replace $VAR or ${VAR} with values from env."""
    import re
    def replacer(m):
        return env.get(m.group(1) or m.group(2), "")
    return re.sub(r'\$\{(\w+)\}|\$(\w+)', replacer, text)


while True:
    try:
        raw = input(f"{'/'.join(current_path)} > ")
    except (EOFError, KeyboardInterrupt):
        print()
        save_fs()
        break

    raw = raw.strip()
    if not raw:
        continue

    # ── expand aliases first ───────────────────────────────
    first_word = raw.split()[0]
    if first_word in aliases:
        raw = aliases[first_word] + raw[len(first_word):]

    # ── expand env vars ────────────────────────────────────
    raw = expand_vars(raw)

    # ── record history (skip bare "history" to avoid noise) ─
    if raw != "history":
        history.append(raw)

    cmd = raw.split()
    if not cmd:
        continue
    command = cmd[0]

    # ══════════════════ BASIC ══════════════════
    if command == "ls":
        dir_ref = get_dir(current_path)
        for k, v in dir_ref.items():
            print("[DIR] " if isinstance(v, dict) else "[FILE]", k)

    elif command == "pwd":
        print("/" + "/".join(current_path))

    elif command == "clear":
        os.system("clear")

    elif command == "exit":
        save_fs()
        break

    # ══════════════════ DIRECTORY ══════════════════
    elif command == "cd":
        if len(cmd) < 2:
            continue
        new_path = resolve_path(cmd[1])
        try:
            if isinstance(get_dir(new_path), dict):
                current_path = new_path
        except Exception:
            print("cd: not found:", cmd[1])

    elif command == "mkdir":
        if len(cmd) < 2:
            print("usage: mkdir <name>"); continue
        get_dir(current_path)[cmd[1]] = {}
        save_fs()

    elif command == "rmdir":
        if len(cmd) < 2:
            print("usage: rmdir <name>"); continue
        name = cmd[1]
        dir_ref = get_dir(current_path)
        if name in dir_ref and isinstance(dir_ref[name], dict):
            del dir_ref[name]
            save_fs()
        else:
            print("rmdir: not a directory or not found:", name)

    # ══════════════════ FILE ══════════════════
    elif command in ["touch", "create"]:
        if len(cmd) < 2:
            print("usage: touch <name>"); continue
        get_dir(current_path)[cmd[1]] = ""
        save_fs()

    elif command == "rm":
        if len(cmd) < 2:
            print("usage: rm <name>"); continue
        name = cmd[1]
        dir_ref = get_dir(current_path)
        if name in dir_ref:
            del dir_ref[name]
            save_fs()
        else:
            print("rm: not found:", name)

    elif command == "write":
        if len(cmd) < 3:
            print("usage: write <file> <content>"); continue
        get_dir(current_path)[cmd[1]] = " ".join(cmd[2:])
        save_fs()

    elif command == "cat":
        if len(cmd) < 2:
            print("usage: cat <file>"); continue
        print(get_dir(current_path).get(cmd[1], ""))

    elif command == "head":
        if len(cmd) < 2:
            print("usage: head <file>"); continue
        content = get_dir(current_path).get(cmd[1], "")
        print("\n".join(content.split("\n")[:5]))

    elif command == "tail":
        if len(cmd) < 2:
            print("usage: tail <file>"); continue
        content = get_dir(current_path).get(cmd[1], "")
        print("\n".join(content.split("\n")[-5:]))

    elif command == "append":
        if len(cmd) < 3:
            print("usage: append <file> <content>"); continue
        get_dir(current_path)[cmd[1]] += "\n" + " ".join(cmd[2:])
        save_fs()

    elif command == "size":
        if len(cmd) < 2:
            print("usage: size <file>"); continue
        print(len(get_dir(current_path).get(cmd[1], "")), "bytes")

    # ══════════════════ COPY / MOVE ══════════════════
    elif command == "copy":
        if len(cmd) < 3:
            print("usage: copy <src> <dst>"); continue
        src, dst = cmd[1], cmd[2]
        dir_ref = get_dir(current_path)
        if src in dir_ref:
            dir_ref[dst] = dir_ref[src]
            save_fs()
        else:
            print("copy: not found:", src)

    elif command in ["move", "rename"]:
        if len(cmd) < 3:
            print(f"usage: {command} <src> <dst>"); continue
        src, dst = cmd[1], cmd[2]
        dir_ref = get_dir(current_path)
        if src in dir_ref:
            dir_ref[dst] = dir_ref[src]
            del dir_ref[src]
            save_fs()
        else:
            print(f"{command}: not found:", src)

    # ══════════════════ INFO ══════════════════
    elif command == "tree":
        import pprint
        pprint.pprint(fs)

    elif command == "count":
        print(len(get_dir(current_path)))

    elif command == "find":
        if len(cmd) < 2:
            print("usage: find <name>"); continue
        name = cmd[1]
        def search(d, path=""):
            for k, v in d.items():
                if k == name:
                    print(path + "/" + k)
                if isinstance(v, dict):
                    search(v, path + "/" + k)
        search(fs)

    elif command == "type":
        if len(cmd) < 2:
            print("usage: type <name>"); continue
        obj = get_dir(current_path).get(cmd[1])
        print("dir" if isinstance(obj, dict) else "file")

    # ══════════════════ TEXT PROCESSING ══════════════════
    elif command == "grep":
        # usage: grep <pattern> <file>
        if len(cmd) < 3:
            print("usage: grep <pattern> <file>"); continue
        pattern, name = cmd[1], cmd[2]
        content = get_dir(current_path).get(name, "")
        matched = [line for line in content.split("\n") if pattern in line]
        if matched:
            print("\n".join(matched))
        else:
            print("(no matches)")

    elif command == "wc":
        # usage: wc <file>   → lines words bytes
        if len(cmd) < 2:
            print("usage: wc <file>"); continue
        content = get_dir(current_path).get(cmd[1], "")
        lines = content.count("\n") + (1 if content else 0)
        words = len(content.split())
        byts  = len(content)
        print(f"  {lines} lines  {words} words  {byts} bytes  {cmd[1]}")

    elif command == "sort":
        # usage: sort <file>   (prints sorted lines)
        if len(cmd) < 2:
            print("usage: sort <file>"); continue
        content = get_dir(current_path).get(cmd[1], "")
        print("\n".join(sorted(content.split("\n"))))

    elif command == "uniq":
        # usage: uniq <file>   (removes consecutive duplicate lines)
        if len(cmd) < 2:
            print("usage: uniq <file>"); continue
        content = get_dir(current_path).get(cmd[1], "")
        lines   = content.split("\n")
        result  = [lines[0]] if lines else []
        for line in lines[1:]:
            if line != result[-1]:
                result.append(line)
        print("\n".join(result))

    elif command == "replace":
        # usage: replace <file> <old> <new>
        if len(cmd) < 4:
            print("usage: replace <file> <old> <new>"); continue
        name, old, new = cmd[1], cmd[2], cmd[3]
        dir_ref = get_dir(current_path)
        if name in dir_ref:
            dir_ref[name] = dir_ref[name].replace(old, new)
            save_fs()
            print("done")
        else:
            print("replace: not found:", name)

    elif command == "upper":
        if len(cmd) < 2:
            print("usage: upper <file>"); continue
        print(get_dir(current_path).get(cmd[1], "").upper())

    elif command == "lower":
        if len(cmd) < 2:
            print("usage: lower <file>"); continue
        print(get_dir(current_path).get(cmd[1], "").lower())

    # ══════════════════ MATH / CALCULATOR ══════════════════
    elif command in ["calc", "bc"]:
        # usage: calc <expression>   e.g.  calc 2 + 2 * 10
        if len(cmd) < 2:
            print("usage: calc <expression>"); continue
        expr = " ".join(cmd[1:])
        try:
            # safe eval: only allow math-safe tokens
            allowed = set("0123456789+-*/()%. eE")
            if not all(c in allowed for c in expr):
                raise ValueError("unsafe characters in expression")
            result = eval(expr, {"__builtins__": {}}, {})
            print(result)
        except Exception as e:
            print("calc error:", e)

    elif command == "abs":
        if len(cmd) < 2:
            print("usage: abs <number>"); continue
        try:
            print(abs(float(cmd[1])))
        except ValueError:
            print("abs: not a number")

    elif command == "round":
        # usage: round <number> [decimals]
        if len(cmd) < 2:
            print("usage: round <number> [decimals]"); continue
        try:
            decimals = int(cmd[2]) if len(cmd) > 2 else 0
            print(round(float(cmd[1]), decimals))
        except ValueError:
            print("round: invalid input")

    # ══════════════════ ENVIRONMENT VARIABLES ══════════════════
    elif command == "set":
        # usage: set VAR value
        if len(cmd) < 3:
            print("usage: set <VAR> <value>"); continue
        env[cmd[1]] = " ".join(cmd[2:])
        print(f"{cmd[1]}={env[cmd[1]]}")

    elif command == "env":
        for k, v in env.items():
            print(f"{k}={v}")

    elif command == "export":
        # alias for set, feels more shell-like: export VAR=value
        if len(cmd) < 2:
            print("usage: export VAR=value"); continue
        pair = cmd[1]
        if "=" in pair:
            k, v = pair.split("=", 1)
            env[k] = v
            print(f"exported {k}={v}")
        else:
            print("export: use VAR=value format")

    elif command == "unset":
        if len(cmd) < 2:
            print("usage: unset <VAR>"); continue
        if cmd[1] in env:
            del env[cmd[1]]
        else:
            print("unset: variable not found:", cmd[1])

    elif command == "printenv":
        # printenv VAR  or  printenv (same as env)
        if len(cmd) > 1:
            print(env.get(cmd[1], ""))
        else:
            for k, v in env.items():
                print(f"{k}={v}")

    # ══════════════════ HISTORY ══════════════════
    elif command == "history":
        if not history:
            print("(empty)")
        else:
            for i, h in enumerate(history, 1):
                print(f"  {i:3}  {h}")

    elif command == "!!":
        # repeat last command
        if len(history) >= 2:          # history[-1] is "!!" itself
            last = history[-2]
            print(f">> {last}")
            history.append(last)
            # re-push to top of loop by printing and executing inline
            cmd = last.split()
            command = cmd[0]           # fall-through won't re-run; just inform
            print("(tip: re-type the command — !! shows it for you)")
        else:
            print("no previous command")

    elif command == "histclear":
        history.clear()
        print("history cleared")

    # ══════════════════ ALIASES ══════════════════
    elif command == "alias":
        # alias ll="ls"   or   alias  (list all)
        if len(cmd) < 2:
            if aliases:
                for k, v in aliases.items():
                    print(f"alias {k}='{v}'")
            else:
                print("(no aliases)")
        else:
            pair = " ".join(cmd[1:])
            if "=" in pair:
                k, v = pair.split("=", 1)
                aliases[k] = v.strip("'\"")
                print(f"alias {k}='{aliases[k]}'")
            else:
                print("alias: use name=command format")

    elif command == "unalias":
        if len(cmd) < 2:
            print("usage: unalias <name>"); continue
        if cmd[1] in aliases:
            del aliases[cmd[1]]
        else:
            print("unalias: not found:", cmd[1])

    # ══════════════════ SYSTEM ══════════════════
    elif command == "ps":
        print("PID  NAME   TIME")
        print(f"  1  pysh   {int(time.time())}")

    elif command == "echo":
        print(" ".join(cmd[1:]))

    elif command == "date":
        print(time.ctime())

    elif command == "whoami":
        print(env.get("USER", "root"))

    elif command == "uptime":
        print(int(time.time()), "seconds since epoch")

    # ══════════════════ NETWORK MOCK ══════════════════
    elif command == "get":
        if len(cmd) < 2:
            print("usage: get <url>"); continue
        print("fetching:", cmd[1])
        time.sleep(0.3)
        print("200 OK (mock)")

    # ══════════════════ HELP ══════════════════
    elif command == "help":
        print("""
╔══════════════════════════════════════════════════════╗
║                   pysh  commands                     ║
╚══════════════════════════════════════════════════════╝

NAVIGATION    ls  pwd  cd  tree  find  count  type

DIRECTORY     mkdir  rmdir

FILE          touch  create  rm  write  cat
              head  tail  append  size
              copy  move  rename

TEXT          grep <pattern> <file>
              wc  sort  uniq  replace  upper  lower

MATH          calc <expr>    e.g. calc 3 * (2 + 5)
              bc  <expr>     same as calc
              abs  round

ENVIRONMENT   set <VAR> <val>   export VAR=val
              env  printenv  unset

HISTORY       history   histclear   !!

ALIASES       alias name=cmd   unalias <name>

SYSTEM        echo  date  whoami  uptime  ps  clear  exit

NETWORK       get <url>
        """)

    else:
        print(f"pysh: command not found: {command}")
