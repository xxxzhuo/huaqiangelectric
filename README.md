# HQEW Crawler (Python MVP)

本仓库已按《hqew-crawler-architecture.md》的实施计划，落地到可执行层面，包含：

- URL 规范化与指纹去重
- 发现层基础实现 + 优先级任务队列
- HTTP 抓取器（重试 + 退避 + 限速）
- 原始页面按日期分区落盘（raw store）
- 产品解析器与标准数据模型
- 变更检测（new/update/relist）
- SQLite 当前快照 + 历史快照 + 变更事件落库
- 调度脚本与端到端 CLI 运行入口
- 单元测试覆盖关键链路

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
python -m crawler.scripts.run_daily_pipeline --offline --db-path data/crawler.db
```

## End-to-end run (network)

```bash
python -m crawler.scripts.run_daily_pipeline \
  --seed-url https://s.hqew.com/ \
  --max-urls 30 \
  --db-path data/crawler.db \
  --raw-dir data/raw
```
