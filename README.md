# hermes-engineering-team

三个 [Hermes Agent](https://github.com/NousResearch/hermes-agent) bot 组成的工程小团队，用来把 [pstack](https://github.com/cursor/plugins/tree/main/pstack) 和 [ub-mode](https://github.com/unclebob/ub-mode) 里的工程原则落到实处。每个人只做一件事，原则之间的冲突放在两个人之间正面发生，由第三个人中立汇总，交给你拍板。

| bot | 干什么 | 能做什么 | 带的原则 |
|---|---|---|---|
| `chief-of-staff` 幕僚长 | 排优先级、准备决策、接续项目；冲突时并排列出双方理由，给一个建议 | 只读：看 git 状态和文档；写文件、改状态的命令在工具层被拦 | evidence |
| `minimalist` 极简工程师 | 唯一写代码的人：先写失败的测试，再做最小改动，用质量工具验证，交付 diff、证据和删掉了什么 | 能写、能在分支上提交；不能推送，不能直接提交到 main/master，不能做不可逆的 git 操作 | ub-mode + evidence |
| `architect` 架构师 | 只评审：结构、类型、边界、幂等 | 只能读文件，没有终端，不能写 | model-the-domain、type-system、boundary、idempotent、encode-lessons |

## 硬约束在工具层，不只是文字

SOUL 里写的规则模型偶尔会忽略，所以真正不能越过的线放在工具层：

- `readonly-guard` 插件（幕僚长、架构师）：拦截 `write_file` 和 `patch`。
- `no-main-commit` 插件（极简工程师）：在 main/master 上提交、同一条命令里先切分支再提交、判断不了目录时，一律拦下。
- `config.yaml` 里的 `approvals.deny`：幕僚长拦 git 写操作、构建、测试、删除等命令；极简工程师只拦推送、`reset --hard`、`clean` 这类不可逆的操作。

## 安装

需要 Hermes Agent 0.22 或更新版本。

```bash
git clone https://github.com/yinjiawen97/hermes-engineering-team.git
hermes profile install ./hermes-engineering-team/chief-of-staff
hermes profile install ./hermes-engineering-team/minimalist
hermes profile install ./hermes-engineering-team/architect
```

然后：

1. **模型**：三个 `config.yaml` 默认接一个 Anthropic 消息格式的 deepseek 兼容服务。把 `http://YOUR-LLM-HOST:PORT` 换成你的服务地址，并在各 profile 的 `.env` 里设置 `HERMES_LAN_DEEPSEEK_KEY`。用别的模型就改 `model` 和 `providers` 两段。
2. **质量工具**（极简工程师用）：
   ```bash
   mkdir -p ~/tools/unclebob && cd ~/tools/unclebob
   git clone https://github.com/unclebob/crapper.git
   git clone https://github.com/unclebob/dryer.git
   git clone https://github.com/unclebob/mutator.git
   ```
   第一次运行时各自建 Python 虚拟环境。它们会在项目根目录写 `.metrics/` 和 `target/`，记得加进项目的 `.gitignore`。
3. **插件**：安装后重启一次 Hermes（或 `hermes gateway restart`），插件才会加载。
4. **Bot Mode**：想让它们出现在桌面端的 Bots 面板里互相 @，开启 `agent.bot_mode_protocol`（三个 config 里已经是 `true`），在 Bots 面板里给它们设标题，再建一个群聊把三个人拉进去。

## 怎么用

- 开始一件事前问幕僚长：现在该先做什么。
- 要改代码时交给极简工程师，指明项目路径。它会切分支、写测试、提交，把 diff 和证据交回来；推送由你来做。
- 让架构师评审极简工程师交来的 diff。两人意见不一致很正常，让幕僚长把分歧并排列出来，你拍板。幕僚长的裁决参考：数据是否在跨越系统边界——跨边界听架构师，不跨边界听极简工程师。

## 许可证

本仓库的原创部分以 MIT 许可证发布，见 [LICENSE](LICENSE)。其中包含的 pstack 原则原文和 ub-mode 的 SKILL.md 来自各自作者，同为 MIT，见 [NOTICE](NOTICE)。
