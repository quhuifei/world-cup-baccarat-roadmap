# 2026 世界杯 · 百家乐大路图

把世界杯实时赛果映射成百家乐「大路图」走势，主队 = 庄，客队 = 闲，常规时间打平 = 和。

## 文件说明

| 文件 | 说明 |
|------|------|
| `index.html` | 单文件前端，包含大路图算法、渲染、交互 |
| `matches.json` | 本地模拟数据，用于演示和测试 |
| `data.json` | 爬虫输出文件，由 GitHub Actions 每小时自动更新 |
| `scraper.py` | Python 爬虫，读取 ESPN 公开 API |
| `.github/workflows/update-scores.yml` | GitHub Actions 定时任务 |

## 本地预览

```bash
cd world-cup-baccarat-roadmap
python3 -m http.server 8080
```

浏览器打开 `http://localhost:8080/index.html`。

页面默认读取 `matches.json`。在顶部输入框改为 `data.json` 或你的真实 API URL，点击「加载数据」即可切换数据源。

## 部署到 GitHub Pages

1. 把本项目推送到 GitHub 仓库。
2. 进入仓库 **Settings → Pages → Source**，选择 `main` 分支 `/ (root)`，保存。
3. 几分钟后访问 `https://<你的用户名>.github.io/<仓库名>/index.html`。
4. 页面里把数据源改成 `https://<你的用户名>.github.io/<仓库名>/data.json`，即可读取爬虫数据。

## 爬虫说明

爬虫使用 ESPN 公开 Scoreboard API，无需 API Key：

```
https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard
```

### GitHub Actions 自动运行

`.github/workflows/update-scores.yml` 已配置为每小时运行一次：

- 抓取最新比分
- 合并到 `data.json`
- 有变更时自动 commit + push

> 免费额度足够：ESPN 公开接口没有严格调用限制，每小时 1 次不会触发封禁。

### 本地手动运行

```bash
python3 scraper.py
```

使用模拟数据（测试用）：

```bash
USE_MOCK=1 python3 scraper.py
```

## 规则速查

- 主队胜 → 红色圆圈（庄赢）
- 客队胜 → 蓝色圆圈（闲赢）
- 常规时间平局 → 绿色斜线（和），点球大战不计入
- 固定 6 行，同结果向下排列，满 6 行向右拐弯
- 结果切换时换列，从第 1 行重新开始
- 连续平局叠加在同一个最新圆圈上，显示数字
