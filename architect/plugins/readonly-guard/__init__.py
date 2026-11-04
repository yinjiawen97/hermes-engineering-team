"""架构师只读：写文件、打补丁、改 skill 一律拦下。架构师没有终端，所以不需要命令规则。"""

WRITE_TOOLS = {"write_file", "patch", "skill_manage"}


def block_writes(tool_name, args, task_id, **kwargs):
    if tool_name in WRITE_TOOLS:
        return {"action": "block",
                "message": "架构师只读，不能写文件，也不能修改 skill。把改动写成方案或 diff 交给用户执行。"}
    return None


def register(ctx):
    ctx.register_hook("pre_tool_call", block_writes)
