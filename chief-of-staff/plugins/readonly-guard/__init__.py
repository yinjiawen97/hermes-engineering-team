"""幕僚长只读：写文件类工具一律拦下。终端命令由 config.yaml 的 approvals.deny 拦。"""

WRITE_TOOLS = {"write_file", "patch"}


def block_writes(tool_name, args, task_id, **kwargs):
    if tool_name in WRITE_TOOLS:
        return {"action": "block",
                "message": "幕僚长只读，不能写文件。把要改的内容写成建议交给用户，或 @architect。"}
    return None


def register(ctx):
    ctx.register_hook("pre_tool_call", block_writes)
