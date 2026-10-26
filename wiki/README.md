# 补充问答与发布 Wiki

Wiki：https://ymbot-5io-wiki.pages.dev/ 。展示名称为 **YMBOT 5IO 开发板系统优化**，GitHub 保留原仓库地址和历史版本链接。

## 补充一个问题

1. 优先更新 `docs/faq/` 对应主题，按“现象、原因、检查或操作、验证范围”组织；记录测试日期和来源。新主题在 `wiki/site.json` 登记，加入 [问答索引](../docs/FAQ.md) 和 README 的入口。
2. 把可公开的实测摘要放入 `board/evidence/`。只保留必要事实；不上传系统/Wi-Fi/ToDesk 口令、远控身份、原始私密日志或未获授权的图纸。
3. 结论有变化时附新证据，保留旧失败记录。收齐帧、错误为0、短测和长测分别陈述；健康检查不等于硬件验收。保留配置与验证分开的入口。
4. 更新 `wiki/site.json` 的整理日期，构建并检查网页。正文直接复用仓库 Markdown，避免网页与操作单两份内容失配。
5. 重新生成根目录 `SHA256SUMS`，提交到 main。GitHub Actions 完成源码、板级离线检查和网页检查后发布至 Cloudflare Pages。失败时不会进入发布步骤；这不是硬件通过标志。

后续调试中有复用价值的问题按此流程沉淀，不需要额外服务器或数据库；目前没有在线编辑器、留言收集或定时自动归档功能。

## 本地预览

需要 Python3.10+；首次安装构建依赖。以下命令在仓库根目录运行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r wiki/requirements.txt
.venv/bin/python wiki/build.py
.venv/bin/python wiki/check.py
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory wiki/dist
```

浏览器打开 `http://127.0.0.1:8765/`。支持全文搜索、代码复制、页内目录与手机导航。正文由独立 HTML 提供，禁用 JavaScript 仍能阅读；搜索需要加载同站的索引，代码复制需浏览器允许剪贴板访问。

维护或 CI 可用 `python3 scripts/update_checksums.py` 更新源码清单，再运行 `python3 scripts/check_source.py`。生成的 `wiki/dist/` 和部署状态不入 Git。

## Cloudflare 发布

站点使用 **Cloudflare Pages Direct Upload + GitHub Actions**，没有运行时后端，不执行设备控制命令。代码块是给读者复制的操作示例。Pages 项目名 `ymbot-5io-wiki`，生产分支 main，上传目录 `wiki/dist`。

仓库 Actions 的私有 Secrets：`WIKI_CLOUDFLARE_API_TOKEN`、`WIKI_CLOUDFLARE_ACCOUNT_ID`。前者只授予目标账户的 Pages Write 权限，不包含 DNS 修改或全局 API Key；Cloudflare 此权限按账户授权，不是仅一个项目。令牌不写入源码、构建产物或日志，PR 不执行发布步骤。凭据变更后在仓库 Secrets 中更新。

手动发布需 Node22+ 和自己的 Cloudflare 登录/受限令牌：

```sh
# 先构建并完成源码/网页检查，再发布
npx --yes wrangler@4.152.0 pages deploy wiki/dist --project-name ymbot-5io-wiki --branch main
```

直接上传项目不能原地转换成 Pages Git Integration；这里由 GitHub Actions 上传，仍可随 main 的提交自动更新。部署详情与回退可在 Cloudflare Pages 项目中查看。参考 [Cloudflare CI 直接上传文档](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/) 和 [Direct Upload 限制](https://developers.cloudflare.com/pages/get-started/direct-upload/)。

## 内容与发布检查

`wiki/check.py` 检查生成页面的本地链接、锚点、搜索索引目标、资源、私有地址及凭据模式；它不主动连接目标设备。修改导航、搜索或样式后需在桌面和手机宽度手动检查；只有文字小修时执行构建与链接检查即可。

保留历史 PDF 的版本说明；不要把旧版报告改标为当前验收。独立 CAN/485 测试结果仍由原始测试和脱敏证据决定，网页上线或 CI 成功不改变这些结论。
