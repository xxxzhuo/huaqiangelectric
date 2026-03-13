# 华强电子网（s.hqew.com）全量产品爬虫架构设计（每日抓取）

## 1. 目标与约束

### 1.1 业务目标
- 覆盖站内全量产品信息（含新增、更新、下架状态）。
- 每日完成一次全量更新，支持中断恢复与失败重试。
- 输出可用于检索、分析、监控与数据服务 API。

### 1.2 非功能目标
- 稳定性：单日抓取成功率 > 99%。
- 时效性：T+0 日可用（每日凌晨启动，上午完成主流程）。
- 可观测性：任务、页面、请求、解析、入库全链路可监控。
- 合规性：遵守 robots、站点条款、频控与数据使用边界。

## 2. 总体架构

```text
调度层 (Airflow/Cron)
  -> URL 发现层 (类目/搜索分页/商家页)
  -> 抓取执行层 (分布式爬虫集群)
  -> 原始落盘层 (Raw HTML/JSON 对象存储)
  -> 解析标准化层 (字段抽取 + 清洗 + 统一模型)
  -> 去重与变更检测层 (指纹/哈希/版本)
  -> 存储层 (MySQL + Elasticsearch + OSS)
  -> 服务层 (查询 API / 下游订阅)
  -> 监控告警层 (Prometheus + Grafana + Alertmanager)
```

## 3. 分层设计

### 3.1 调度层
- **推荐方案**：Airflow（主），Cron（备）。
- DAG 拆分：
  1. seed 初始化（站点入口、类目、搜索字母表）
  2. URL 发现与去重入队
  3. 详情抓取
  4. 解析与标准化
  5. upsert 入库
  6. 差异计算与下架标记
  7. 质量校验与报表输出
- 支持 `backfill`：按日期重跑，避免全链路重复抓。

### 3.2 URL 发现层
- 来源：
  - 类目页分页
  - 搜索结果分页
  - 商家店铺商品列表
  - 站点内推荐/关联商品链接
- 队列字段建议：
  - `url`, `url_type`, `depth`, `discover_date`, `priority`, `retry_count`, `fingerprint`
- 去重策略：
  - URL 规范化（去无关 query、统一 host/path）
  - 指纹去重（MD5(url_normalized)）

### 3.3 抓取执行层
- 技术栈建议：
  - Scrapy + Redis（分布式）
  - Playwright 仅用于少量动态页面回退
- 关键策略：
  - 自适应并发（按域名、响应时间、错误率动态调节）
  - 限速（QPS 上限、随机抖动）
  - 失败重试（网络错误/5xx/超时指数退避）
  - 代理池（按可用性评分轮换）
  - UA 池与 Header 模板轮换
- 断点续跑：
  - 请求状态写入 Redis/Kafka
  - 任务粒度 checkpoint

### 3.4 原始落盘层
- 落盘对象：
  - 请求元数据（时间、状态码、耗时、代理、UA）
  - 原始 HTML / JSON 响应体
- 存储建议：
  - OSS/S3 按 `dt=YYYY-MM-DD/site=.../type=...` 分区
  - 保留周期：30~90 天（支持回溯解析）

### 3.5 解析标准化层
- 统一产品模型（核心字段）：
  - 产品唯一键：`site_product_id`（若无则 URL 指纹）
  - 标题、品牌、型号、封装、参数、库存、价格区间
  - 最小起订量、交期、卖家信息、地区、更新时间
  - 类目路径、图片 URL、详情描述、数据来源 URL
- 解析流程：
  1. DOM 解析/XPath/CSS Selector
  2. 文本清洗（空白、单位统一、全半角）
  3. 字段映射到标准 schema
  4. 枚举归一（单位、币种、地区）
- 质量规则：
  - 必填字段校验（标题、型号、卖家、来源 URL）
  - 价格/库存数值范围校验

### 3.6 去重与变更检测层
- 去重维度：
  - 同商品跨 URL 去重（型号 + 卖家 + 品牌组合键）
  - 同 URL 版本去重（内容哈希）
- 变更检测：
  - 哈希比对（标题/价格/库存/参数分字段 hash）
  - 变更类型：`new`, `update`, `delist`, `relist`
- 下架判定：
  - 连续 N 天未抓到或页面 404/下架标记

### 3.7 存储层
- **MySQL（事务主存）**
  - `product_current`：当前快照
  - `product_history`：历史版本（SCD2）
  - `crawl_task_log`：任务日志
- **Elasticsearch（检索）**
  - 支持型号、品牌、参数、地区、卖家组合检索
- **对象存储**
  - 保存原始页面与解析失败样本

### 3.8 服务与消费层
- 提供内部 API：
  - `/products/search`
  - `/products/{id}`
  - `/products/changes?date=...`
- 数据订阅：
  - Kafka topic 按变更事件推送（新增/降价/补货等）

### 3.9 监控与告警层
- 采集指标：
  - 抓取成功率、平均响应时延、429/403 比例
  - 每小时抓取量、解析成功率、入库延迟
  - 每日新增/更新/下架数量
- 告警规则：
  - 抓取成功率低于阈值
  - 某核心类目抓取量异常下跌
  - 解析字段空值率异常升高

## 4. 每日抓取作业编排（建议）

### 4.1 时间窗
- 00:30 启动 URL 发现
- 01:00~06:00 主抓取
- 06:00~08:00 解析入库 + 差异比对
- 08:30 输出日报 + 告警汇总

### 4.2 增量优先策略
- 高热度类目与最近 7 天活跃卖家优先抓。
- 低活跃页面采用隔日/隔周巡检，降低资源消耗。

## 5. 反爬与稳定性策略
- 严格频控：分时段限速，避免突发流量。
- IP 健康分：失败率过高自动摘除。
- 失败分级：网络异常重试，结构变更进入人工/规则回退。
- 页面结构漂移检测：DOM 节点签名监控，触发解析器切换。

## 6. 数据模型（简版）

### 6.1 product_current
- `id` (PK)
- `site`
- `site_product_id`
- `url`
- `title`
- `brand`
- `model`
- `package`
- `price_min`, `price_max`, `currency`
- `stock`
- `moq`
- `seller_name`, `seller_id`, `seller_region`
- `category_path`
- `param_json`
- `status`（online/delist）
- `first_seen_at`, `last_seen_at`, `updated_at`

### 6.2 product_history
- `id` (PK)
- `product_id`
- `version`
- `field_diff_json`
- `snapshot_json`
- `captured_at`

## 7. 部署建议
- 容器化：Docker + K8s
- 组件拆分：
  - scheduler
  - discoverer
  - crawler-worker
  - parser-worker
  - upsert-worker
- 弹性策略：
  - 抓取高峰扩容 crawler-worker
  - 解析瓶颈扩容 parser-worker

## 8. 安全与合规
- 检查 robots 与站点条款，限制访问路径。
- 不抓取个人敏感信息；仅保留业务必要字段。
- 全链路审计日志，支持数据删除与溯源。

## 9. 里程碑（4 周）
- 第 1 周：站点摸底、URL 发现器、样本解析器
- 第 2 周：分布式抓取 + 原始落盘 + 基础监控
- 第 3 周：标准化入库 + 变更检测 + API
- 第 4 周：压测、稳定性优化、日报与告警完善

## 10. MVP 范围（先上线）
- 覆盖 TOP 类目（占全站 70% 商品量）
- 每日一次全量 + 关键类目二次补抓
- 提供新增/变更/下架三类日报

## 11. Python 实施分步计划（按该架构落地）

### 11.1 技术选型（Python）
- 语言与运行时：Python 3.11
- 抓取框架：Scrapy + scrapy-redis
- 动态页面回退：Playwright for Python
- 调度编排：Apache Airflow（Python DAG）
- 消息队列：Redis Stream 或 Kafka（二选一）
- 存储：MySQL + Elasticsearch + MinIO/S3
- 数据建模与校验：Pydantic
- 可观测：Prometheus + Grafana + Sentry

### 11.2 代码仓结构建议
```text
crawler/
  dags/                     # Airflow DAG 定义
  spiders/                  # Scrapy spiders（discover/detail）
  parsers/                  # 字段抽取器（按页面类型）
  pipelines/                # 清洗、标准化、入库
  models/                   # Pydantic schema
  storage/                  # MySQL/ES/OSS 读写封装
  anti_bot/                 # 限速、代理池、UA策略
  monitor/                  # 指标埋点、健康检查
  scripts/                  # 回填、修复、重跑工具
  tests/                    # 单测/集成测试
```

### 11.3 分 8 步执行（建议 4~6 周）
1. **站点摸底与字段定义（第 1 周）**
   - 产出 URL 类型清单（类目页、搜索页、详情页、店铺页）。
   - 固化产品标准字段 schema（Pydantic）与必填规则。
   - 抽样 200~500 页面，形成解析样本库。

2. **URL 发现器开发（第 1~2 周）**
   - 实现 `discover_spider`，覆盖分页与关联链接。
   - 实现 URL 规范化、MD5 指纹去重、优先级入队。
   - 输出 discover 指标：新增 URL 数、重复率、失败率。

3. **详情抓取器开发（第 2 周）**
   - 实现 `detail_spider`，支持断点续抓与指数退避重试。
   - 引入限速/并发动态调节、代理与 UA 轮换。
   - 接入 Playwright 回退（仅命中疑难页面）。

4. **原始数据落盘与可回放（第 2~3 周）**
   - HTML/JSON 与请求元信息按日期分区写入对象存储。
   - 建立 `raw -> parse` 回放脚本，支持解析器迭代重放。

5. **解析与标准化（第 3 周）**
   - 按页面模板拆分 parser，输出统一 `ProductRecord`。
   - 做单位/币种/地区归一化，异常值打标进入隔离队列。
   - 关键字段空值率 > 阈值时自动告警。

6. **入库与变更检测（第 3~4 周）**
   - `product_current` 做 upsert，`product_history` 做版本快照。
   - 计算字段级 hash，产出 `new/update/delist/relist` 事件。
   - 下架策略：连续 N 天未命中 + 页面状态辅助判定。

7. **调度编排与日报（第 4 周）**
   - Airflow DAG 串联 discover -> crawl -> parse -> upsert -> diff。
   - 增加任务 SLA、失败重跑、backfill 参数化。
   - 输出日报：抓取量、成功率、新增/更新/下架统计。

8. **压测与上线（第 5~6 周）**
   - 压测目标：日抓取峰值、解析吞吐、入库延迟。
   - 灰度策略：先 TOP 类目，后全类目逐步放量。
   - 建立 runbook（故障定位、恢复步骤、回滚策略）。

### 11.4 每一步的验收标准（DoD）
- 抓取层：成功率 >= 99%，429/403 比例在预设阈值内。
- 解析层：核心字段完整率 >= 98%，解析异常可追溯。
- 存储层：入库幂等，无重复主键冲突，历史版本可回放。
- 调度层：DAG 全链路可重跑，单任务失败可局部恢复。
- 业务层：每日 08:30 前产出可用数据与差异报告。

### 11.5 首版开发任务拆分（工程视角）
- `Task A`：`discover_spider` + URL 队列去重
- `Task B`：`detail_spider` + anti-bot 中间件
- `Task C`：`parser` + `ProductRecord` schema
- `Task D`：`mysql_writer` + `es_indexer`
- `Task E`：`diff_worker` + 下架判定
- `Task F`：Airflow DAG + 监控告警 + 日报脚本

> 建议先完成 A/B/C，打通“可抓 + 可解析 + 可落库”最小闭环，再推进 D/E/F。
