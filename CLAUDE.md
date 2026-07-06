# CLAUDE.md

本文件为 AI 助手（Claude / CatPaw 等）提供项目上下文和 Agent skills 配置。

## 项目概述

browser-use 是一个基于 Playwright + LLM 的浏览器自动化 Agent 项目，包含 Python 后端（`browser_use/`）和 React 前端（`frontend/`）。

详细架构请参阅 `ARCHITECTURE.md`。

## Agent skills

### Issue tracker

Issues 以本地 markdown 文件形式存放在 `.scratch/` 目录下。详见 `docs/agents/issue-tracker.md`。

### Triage labels

使用默认的五标签词汇（needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix）。详见 `docs/agents/triage-labels.md`。

### Domain docs

单一上下文布局：一个 `CONTEXT.md` + `docs/adr/` 在仓库根目录。详见 `docs/agents/domain.md`。
