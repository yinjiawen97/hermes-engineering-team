"""幕僚长只读：只能写看板共享目录和自己的缓存目录，其余一律拦下。

覆盖文件工具（write_file、patch，含 V4A 补丁里的路径）和终端里常见的写法：
重定向、curl/wget 下载、sed/perl 原地修改、python/node 一行脚本写文件。
判断不了写到哪里时一律拦下（fail closed）。tee/cp/mv/rm 由 config.yaml 的 approvals.deny 拦。
"""
import os
import re
from pathlib import Path

PROFILE_HOME = Path(__file__).resolve().parents[2]          # ~/.hermes/profiles/chief-of-staff
HERMES_ROOT = PROFILE_HOME.parents[1]                        # ~/.hermes
ALLOWED = [HERMES_ROOT / "kanban" / "boards", PROFILE_HOME / "cache"]

MSG = ("幕僚长只读：只能写看板目录（~/.hermes/kanban/boards/）和自己的缓存目录（cache/），"
       "这次要写的位置不在其中。不要换一种写法重试；把要改的内容写成建议交给用户，或 @minimalist。")

TOKEN = r"(\"[^\"]+\"|'[^']+'|[^\s;&|<>()]+)"
CD = re.compile(r"(?:^|&&|;|\|\|)\s*cd\s+" + TOKEN)
REDIRECT = re.compile(r"(?<![<>&\d])(?:\d|&)?>>?(?!&)\s*" + TOKEN)   # > f, >> f, 2> f, &> f；不含 2>&1
CURL_OUT = re.compile(r"\bcurl\b[^;&|]*?\s(?:-o|--output)\s+" + TOKEN)
CURL_REMOTE_NAME = re.compile(r"\bcurl\b[^;&|]*?\s(?:-O|--remote-name|-J)\b")
WGET = re.compile(r"\bwget\b")
WGET_OUT = re.compile(r"\bwget\b[^;&|]*?\s(?:-O|--output-document)\s+" + TOKEN)
IN_PLACE = re.compile(r"\b(?:sed|perl)\b[^;&|]*?\s-[a-zA-Z]*i")
SCRIPT_WRITES = re.compile(r"\b(?:python3?|node|ruby|perl)\b[^;&|]*?\s-[ce]\b.*"
                           r"(?:open\(|write_text|write_bytes|writeFile|appendFile|File\.write|shutil\.|os\.(?:rename|replace|remove))")
V4A_PATHS = re.compile(r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+)$|^\*\*\* Move to:\s*(.+)$", re.M)


def _clean(token):
    return os.path.expanduser(token.strip("\"'"))


def allowed(path, cwd=None):
    """path 是否落在允许的目录里。相对路径需要已知的 cwd，否则不放行。"""
    p = Path(_clean(path))
    if not p.is_absolute():
        if not cwd:
            return False
        p = Path(_clean(cwd)) / p
    real = Path(os.path.realpath(p))
    return any(real == root.resolve() or root.resolve() in real.parents for root in ALLOWED)


HEREDOC_BODY = re.compile(r"<<-?\s*([\"']?)(\w+)\1[^\n]*\n.*?\n\2\b", re.S)
SINGLE_QUOTED = re.compile(r"(>\s*)?'[^']*'")


def _strip_data(command):
    """去掉不是命令的部分：heredoc 正文、单引号里的脚本（awk/sed 表达式里的 > 不是重定向）。"""
    command = HEREDOC_BODY.sub("<<HEREDOC", command)
    return SINGLE_QUOTED.sub(lambda m: m.group(0) if m.group(1) else "''", command)


def _cwd(command, workdir):
    """按顺序累加 cd，相对路径接在当前目录后面；一开始不知道在哪就保持未知。"""
    cwd = _clean(workdir) if workdir else None
    for d in CD.findall(command):
        d = _clean(d)
        cwd = d if os.path.isabs(d) else (os.path.join(cwd, d) if cwd else None)
    return cwd


# 解释器从 heredoc / stdin 读脚本：脚本正文里有写文件的操作就拦（正文会被 _strip_data 去掉，所以先查）
INTERPRETER_HEREDOC = re.compile(r"\b(?:python3?|node|ruby|perl|bash|sh|zsh)\b[^\n;&|]*<<")
WRITE_OPS = re.compile(r"open\([^)]*['\"][wax]\+?b?['\"]|write_text|write_bytes|writeFile|appendFile|File\.write"
                       r"|shutil\.|os\.(?:rename|replace|remove|unlink|makedirs)|extractall|urlretrieve|\.save\("
                       r"|(?<![<>&\d])>>?\s*[^\s&>]")


def terminal_reason(command, workdir=None):
    """终端命令会写到允许范围以外时返回拦截理由，否则 None。"""
    if INTERPRETER_HEREDOC.search(command):
        body = "\n".join(m.group(0) for m in HEREDOC_BODY.finditer(command))
        if WRITE_OPS.search(body):
            return MSG
    command = _strip_data(command)
    cwd = _cwd(command, workdir)
    targets = [t for t in REDIRECT.findall(command) if _clean(t) != "/dev/null"]
    targets += CURL_OUT.findall(command) + WGET_OUT.findall(command)
    for t in targets:
        if not allowed(t, cwd):
            return MSG
    # 写到 cwd、文件名由远端决定的下载：cwd 必须在允许范围里
    if (CURL_REMOTE_NAME.search(command) or (WGET.search(command) and not WGET_OUT.search(command))) \
            and not (cwd and allowed(cwd)):
        return MSG
    # 原地修改和一行脚本写文件：只有整条命令都在允许目录里执行时放行
    if (IN_PLACE.search(command) or SCRIPT_WRITES.search(command)) and not (cwd and allowed(cwd)):
        return MSG
    return None


def guard(tool_name, args, task_id, **kwargs):
    if tool_name == "skill_manage":   # 不许改自己的规则；读 skill 用 skill_view
        return {"action": "block", "message": "幕僚长不能修改 skill。要改规则请交给用户。"}
    if tool_name in ("write_file", "patch"):
        paths = [args.get("path")] if args.get("path") else []
        for add, move in V4A_PATHS.findall(str(args.get("patch") or "")):
            paths.append(add or move)
        if not paths or not all(allowed(p.strip()) for p in paths):
            return {"action": "block", "message": MSG}
        return None
    if tool_name == "terminal":
        reason = terminal_reason(str(args.get("command") or ""), args.get("workdir"))
        return {"action": "block", "message": reason} if reason else None
    return None


def register(ctx):
    ctx.register_hook("pre_tool_call", guard)
