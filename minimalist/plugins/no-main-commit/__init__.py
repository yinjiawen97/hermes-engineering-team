"""极简工程师不能直接在 main/master 上提交：先切分支再提交。

判断不了在哪个目录、哪个分支提交时一律拦下（fail closed），让 agent 写清楚再来。
"""
import os
import re
import subprocess

PROTECTED = {"main", "master"}
COMMIT = re.compile(r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+commit\b")
GIT_C_DIR = re.compile(r"\bgit\s+(?:-c\s+\S+\s+)*-C\s+(\"[^\"]+\"|'[^']+'|\S+)")
CD = re.compile(r"(?:^|&&|;|\|\|)\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)")
SWITCHES_BRANCH = re.compile(r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+(?:checkout|switch)\b")


def _unquote(s):
    return os.path.expanduser(s.strip("\"'"))


def current_branch(path):
    out = subprocess.run(["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
                         capture_output=True, text=True, timeout=10)
    return out.stdout.strip() if out.returncode == 0 else None


def decide(command, workdir, branch_of=current_branch):
    """返回拦截理由；放行时返回 None。"""
    commit = COMMIT.search(command)
    if not commit:
        return None
    before = command[:commit.start()]
    if SWITCHES_BRANCH.search(before):
        return "切分支和提交请分成两条命令：先 git switch -c <新分支>，再单独提交。"
    m = GIT_C_DIR.search(command[commit.start():commit.end()])
    cds = CD.findall(before)
    path = _unquote(m.group(1)) if m else _unquote(cds[-1]) if cds else workdir
    if not path:
        return "提交前请用 workdir 参数或 git -C <目录> 写明在哪个仓库提交。"
    branch = branch_of(path)
    if branch is None:
        return f"判断不了 {path} 当前在哪个分支，提交被拦下。"
    if branch in PROTECTED:
        return f"不能直接在 {branch} 上提交。先 git switch -c <新分支>，再提交；推送交给用户。"
    return None


def guard(tool_name, args, task_id, **kwargs):
    if tool_name != "terminal":
        return None
    reason = decide(str(args.get("command") or ""), args.get("workdir"))
    return {"action": "block", "message": reason} if reason else None


def register(ctx):
    ctx.register_hook("pre_tool_call", guard)
