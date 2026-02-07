# Hogwarts-bench

使用《哈利·波特》小说系列评估大语言模型长上下文能力的自动化测试框架。

## 概述

Hogwarts-bench 是一个"大海捞针"风格的基准测试工具，系统性地评估大语言模型在长文档中不同上下文长度和位置处的事实检索、细节记忆和信息综合能力。

该框架使用《哈利·波特》小说系列作为标准化语料库进行测试：
- **事实检索**：模型能否在不同位置找到特定信息？
- **细节记忆**：模型能否记住文本中的细粒度细节？
- **信息综合**：模型能否整合来自多个部分的信息？
- **位置偏差**：在某些上下文位置，性能是否会下降？

### 主要特性

- **自动问题生成**：从任意小说文本生成多样化的测试问题
- **灵活的采样策略**：分层或随机采样以覆盖不同文本区域
- **并发处理**：并行 API 调用以加快生成和测试速度
- **健壮的错误处理**：针对 API 失败的重试逻辑和回退策略
- **交互式报告**：带有可视化和错误分析的 HTML 报告
- **可定制提示词**：易于修改的 JSON 模板，适用于不同用例

### 架构

该框架由三个独立的 CLI 工具组成，可以顺序执行或单独执行：

1. **问题生成器** (`generate.py`)：从小说文本自动生成测试问题
2. **测试工具** (`test.py`)：在目标 LLM 上执行测试并收集结果
3. **报告生成器** (`report.py`)：分析结果并生成交互式 HTML 报告

## 安装

### 前置条件

- Python 3.8 或更高版本
- pip 包管理器

### 安装依赖

```bash
pip install -r requirements.txt
```

或以开发模式安装包：

```bash
pip install -e .
```

## 配置

1. 复制示例配置文件：

```bash
cp .env.example .env
```

2. 编辑 `.env` 并填入您的 API 凭据：

```bash
# 必需
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=anthropic/claude-3-sonnet

# 可选（已提供默认值）
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000
DEFAULT_TIMEOUT=60
DEFAULT_CONCURRENCY=5
DEFAULT_RETRY_TIMES=3
DEFAULT_RETRY_DELAY=5
```

## 使用方法

### 快速开始

以下是完整的工作流程示例：

```bash
# 1. 从小说生成 200 个问题
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --output data/questions.jsonl

# 2. （可选）验证生成的问题
python -m src.validate \
    --novel data/harry_potter_1.txt \
    --questions data/questions.jsonl \
    --output data/questions_validated.jsonl \
    --valid-only

# 3. 使用 50k token 上下文测试 LLM
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions_validated.jsonl \
    --context_length 50000 \
    --output data/results.jsonl

# 4. 生成交互式 HTML 报告
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html
```

### 1. 生成问题

问题生成器使用 LLM 从小说文本创建结构化的测试问题。

#### 基本用法

```bash
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --output data/questions.jsonl
```

#### 使用所有选项的高级用法

```bash
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --sampling_strategy stratified \
    --context_window_size 500 \
    --concurrency 10 \
    --retry_times 3 \
    --output data/questions.jsonl
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--novel` | 是 | - | 小说文本文件路径（UTF-8 编码） |
| `--question_nums` | 是 | - | 要生成的问题数量 |
| `--sampling_strategy` | 否 | `stratified` | 采样方法：`stratified` 或 `random` |
| `--context_window_size` | 否 | `500` | 上下文提取的 token 窗口大小 |
| `--concurrency` | 否 | `5` | 并发 API 请求数 |
| `--retry_times` | 否 | `3` | 失败请求的最大重试次数 |
| `--output` | 是 | - | 输出 JSONL 文件路径 |

#### 采样策略

- **分层采样**（推荐）：将小说分成 50k token 的层，并从每层均匀采样。这确保了对整部小说的覆盖。
- **随机采样**：在整部小说中随机采样位置。适用于无偏测试，但可能会遗漏某些区域。

#### 输出格式

输出是一个 JSONL 文件，每行包含：

```json
{
  "question": "哈利使用了什么咒语？",
  "question_type": "single_choice",
  "choice": {
    "a": "除你武器",
    "b": "昏昏倒地",
    "c": "盔甲护身",
    "d": "呼神护卫"
  },
  "answer": ["a"],
  "position": {
    "start_pos": 12500,
    "end_pos": 12650
  }
}
```


### 2. 验证问题（可选）

验证工具通过让验证 LLM 独立回答每个问题并比较结果来验证生成的问题质量。

#### 基本用法

```bash
python -m src.validate \
    --novel data/harry_potter_1.txt \
    --questions data/questions.jsonl \
    --output data/questions_validated.jsonl
```

#### 使用所有选项的高级用法

```bash
python -m src.validate \
    --novel data/harry_potter_1.txt \
    --questions data/questions.jsonl \
    --output data/questions_validated.jsonl \
    --concurrency 5 \
    --confidence-threshold medium \
    --similarity-threshold 0.8 \
    --valid-only
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--novel` | 是 | - | 小说文本文件路径 |
| `--questions` | 是 | - | 待验证的问题 JSONL 文件路径 |
| `--output` | 是 | - | 验证后问题的输出路径 |
| `--concurrency` | 否 | `5` | 并发验证请求数 |
| `--confidence-threshold` | 否 | `medium` | 最低置信度级别：`low`、`medium`、`high` |
| `--similarity-threshold` | 否 | `0.8` | 证据匹配的最低相似度（0.0-1.0） |
| `--valid-only` | 否 | `false` | 仅输出通过验证的问题 |
| `--verbose` | 否 | `false` | 启用详细日志 |

#### 验证检查项

验证器执行以下检查：
1. **答案验证**：让验证 LLM 独立回答问题
2. **答案比对**：将验证答案与标注答案进行比较
3. **证据匹配**：验证源上下文中是否存在支持证据
4. **置信度评估**：检查 LLM 对其答案的置信度级别

#### 输出格式

输出包含每个问题的验证元数据：

```json
{
  "question": "哈利使用了什么咒语？",
  "question_type": "single_choice",
  "choice": {"a": "除你武器", "b": "昏昏倒地", "c": "盔甲护身", "d": "呼神护卫"},
  "answer": ["a"],
  "position": {"start_pos": 12500, "end_pos": 12650},
  "validation": {
    "is_valid": true,
    "verification_answer": ["a"],
    "answer_match": true,
    "evidence_found": true,
    "confidence": "high"
  }
}
```


### 3. 运行测试

测试工具使用生成的问题在目标 LLM 上执行测试。

#### 基本用法

```bash
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results.jsonl
```

#### 使用所有选项的高级用法

```bash
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --padding_size 500 \
    --concurrency 5 \
    --output data/results.jsonl
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--novel` | 是 | - | 小说文本文件路径（与生成时使用的相同） |
| `--data_set` | 是 | - | 问题集 JSONL 文件路径 |
| `--context_length` | 是 | - | 提供给 LLM 的总上下文长度（token 数） |
| `--padding_size` | 否 | `500` | 缓冲 token 数，确保答案不被截断 |
| `--concurrency` | 否 | `5` | 并发测试请求数 |
| `--max-questions` | 否 | 全部 | 最大测试题目数量，按深度均匀采样 |
| `--output` | 是 | - | 输出结果 JSONL 文件路径 |

#### 上下文长度指南

- **8k tokens**：测试短上下文性能
- **32k tokens**：测试中等上下文性能
- **50k-100k tokens**：测试长上下文性能
- **128k+ tokens**：测试扩展上下文性能

该工具会自动过滤答案位置超出上下文窗口（考虑填充）的问题。

#### 输出格式

输出是一个 JSONL 文件，每行包含：

```json
{
  "question": "哈利使用了什么咒语？",
  "question_type": "single_choice",
  "choice": {"a": "除你武器", "b": "昏昏倒地", "c": "盔甲护身", "d": "呼神护卫"},
  "correct_answer": ["a"],
  "model_answer": ["a"],
  "parsing_status": "success",
  "position": {"start_pos": 12500, "end_pos": 12650},
  "score": 1.0
}
```

### 4. 生成报告

报告生成器创建带有可视化和指标的交互式 HTML 报告。

#### 基本用法

```bash
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html
```

#### 使用所有选项的高级用法

```bash
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html \
    --error_examples 15
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--results` | 是 | - | 测试结果 JSONL 文件路径 |
| `--output` | 是 | - | 输出 HTML 报告文件路径 |
| `--error_examples` | 否 | `10` | 报告中显示的错误案例数量 |

#### 报告内容

生成的 HTML 报告包括：

1. **摘要部分**
   - 测试配置（模型、上下文长度等）
   - 总体指标（准确率、精确率、召回率、F1 分数）
   - 问题类型分布

2. **交互式散点图**
   - X 轴：小说中的 token 位置
   - Y 轴：性能分数（0.0 到 1.0）
   - 颜色编码：绿色（正确）、黄色（部分正确）、红色（错误）、灰色（异常）
   - 悬停提示显示问题详情
   - 趋势线显示跨位置的性能变化

3. **错误分析**
   - 错误或部分正确答案的随机样本
   - 显示问题、正确答案、模型答案和分数
   - 帮助识别模型失败的模式

### 5. 生成热力图

热力图生成器创建可视化图表，展示问题在上下文中的分布覆盖情况以及模型在不同上下文区域的正确率。

#### 基本用法

```bash
# 生成问题覆盖度热力图
python -m src.heatmap \
    --mode coverage \
    --questions data/questions.jsonl \
    --output reports/coverage.html

# 生成模型正确率热力图
python -m src.heatmap \
    --mode accuracy \
    --results data/results.jsonl \
    --output reports/accuracy.html

# 生成组合热力图（覆盖度 + 正确率对齐展示）
python -m src.heatmap \
    --mode combined \
    --questions data/questions.jsonl \
    --results data/results.jsonl \
    --output reports/combined.html
```

#### 使用所有选项的高级用法

```bash
python -m src.heatmap \
    --mode combined \
    --questions data/questions.jsonl \
    --results data/results.jsonl \
    --output reports/heatmap.html \
    --bins 50 \
    --context-length 200000
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--mode` | 是 | - | 热力图模式：`coverage`（覆盖度）、`accuracy`（正确率）或 `combined`（组合） |
| `--questions` | 视模式 | - | 问题集 JSONL 文件路径（coverage 和 combined 模式必需） |
| `--results` | 视模式 | - | 测试结果 JSONL 文件路径（accuracy 和 combined 模式必需） |
| `--output` | 是 | - | 输出 HTML 文件路径 |
| `--bins` | 否 | `50` | 将上下文划分的区间数量 |
| `--context-length` | 否 | `200000` | 上下文总长度（token 数） |

#### 热力图模式

- **coverage（覆盖度）**：展示问题在上下文各区域的分布密度，使用蓝色渐变
- **accuracy（正确率）**：展示模型在各区域的回答正确率，使用红-黄-绿渐变（灰色表示无数据）
- **combined（组合）**：将覆盖度和正确率对齐展示在同一图表中，便于对比分析

#### 热力图特性

- 自动从 JSONL 文件提取模型名称和数据集名称
- 顶部显示项目标题 "KCORES Hogwarts Bench"
- 右下角嵌入项目 Logo（导出 PNG 时会包含）
- 支持交互式悬停查看详细信息
- 支持导出为 PNG 图片

### 6. 深度感知测试

深度感知测试评估 LLM 在不同上下文深度的召回准确率。与传统模式总是将证据放在上下文开头不同，此模式动态构建上下文，将证据放置在不同深度位置（0%、25%、50%、75%、100%）。

#### 基本用法

```bash
# 均匀分布到各深度和上下文长度
python -m src.test \
    --novel data/harry_potter_5.txt \
    --data_set data/harry_potter_5_questions_512_context_512k_v2_validated.jsonl \
    --depth-mode uniform \
    --context-lengths 4000,8000,16000,32000,64000,128000,192000,200000 \
    --output report/results_depth.jsonl

# 固定深度测试（例如，仅在 50% 深度测试）
python -m src.test \
    --novel data/harry_potter_5.txt \
    --data_set data/questions_validated.jsonl \
    --depth-mode fixed \
    --depth 0.5 \
    --context-lengths 128000 \
    --output data/results_fixed.jsonl
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--depth-mode` | 否 | `legacy` | 深度模式：`legacy`、`uniform` 或 `fixed` |
| `--depth` | fixed 模式必需 | - | 固定深度值（0.0-1.0） |
| `--context-lengths` | 深度模式必需 | - | 逗号分隔的上下文长度（如 64000,128000,200000） |
| `--max-questions` | 否 | 全部 | 最大测试题目数量，按深度均匀采样 |

#### 上下文长度验证

工具会在测试前验证 `--context-lengths` 参数：
- 上下文长度不能超过小说的总 token 数
- 上下文长度必须足够大，能够容纳问题证据和填充
- 至少要有部分问题可以在给定的上下文长度下进行测试

如果验证失败，工具会报告具体错误并给出建议。

#### 深度模式

- **legacy**（默认）：传统测试模式，使用前 N 个 token 作为上下文
- **uniform**：将问题均匀分配到 5 个深度区间（0%、25%、50%、75%、100%）和所有指定的上下文长度
- **fixed**：所有问题在单一固定深度测试

#### 输出格式

深度感知结果包含额外字段：

```json
{
  "question": "哈利使用了什么咒语？",
  "correct_answer": ["a"],
  "model_answer": ["a"],
  "score": 1.0,
  "depth": 0.5,
  "depth_bin": "50%",
  "test_context_length": 128000
}
```

### 7. 恢复模式（Recovery Mode）

当测试过程中因 API 欠费、网络超时或其他错误导致测试中断时，可以使用恢复模式重新运行失败的测试项目，而无需重新测试已成功的项目，从而节省 API 费用。

#### 使用场景

- API 欠费导致测试中断
- 网络超时导致部分测试失败
- 系统错误导致测试结果不完整
- 需要重试之前失败的测试项目

#### 基本用法

```bash
# 恢复深度感知测试
python -m src.test \
    --novel data/harry_potter_5.txt \
    --data_set data/harry_potter_5_questions_512_context_512k_v2_validated.jsonl \
    --depth-mode uniform \
    --context-lengths 4000,8000,16000,32000,64000,128000,192000,256000 \
    --recovery report/results-qwen3-max-thinking-depth-turn-1.jsonl \
    --output report/results-qwen3-max-thinking-depth-turn-1-recovered.jsonl

# 恢复传统模式测试
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --recovery data/results.jsonl \
    --output data/results_recovered.jsonl

# 恢复无参考模式测试
python -m src.test \
    --no-reference \
    --data_set data/questions_with_summary.jsonl \
    --recovery data/results_no_ref.jsonl \
    --output data/results_no_ref_recovered.jsonl
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--recovery` | 否 | - | 上次测试结果文件路径，启用恢复模式 |

其他参数与正常测试模式相同，需要保持一致以确保正确恢复。

#### 恢复逻辑

恢复模式会识别以下类型的失败结果并重新测试：
- `parsing_status` 为 `error`（API 错误，如欠费）
- `parsing_status` 为 `timeout`（请求超时）
- `parsing_status` 为 `context_build_error`（上下文构建错误）
- `parsing_status` 为 `parsing_error`（响应解析失败）

以下状态的结果会被保留，不会重新测试：
- `parsing_status` 为 `success`（成功解析）
- `parsing_status` 为 `regex_extracted`（正则提取成功）

#### 输出说明

恢复模式会输出详细的恢复统计信息：

```
============================================================
RECOVERY MODE - Depth-Aware Tests
============================================================
Loading previous results from: report/results.jsonl
Loaded 369 previous results
  Successful results (will keep): 350
  Failed results (will re-run): 19
  Failure breakdown:
    Error: 15
    Timeout: 4
    Context build error: 0
...
Recovery results:
  Successfully recovered: 18
  Still failed: 1
Final merged results: 369
```

#### 注意事项

- 恢复模式需要使用与原始测试相同的参数（小说路径、问题集、上下文长度等）
- 恢复后的结果文件会包含原始成功的结果和新恢复的结果
- 如果某些测试仍然失败，可以多次运行恢复模式
- 建议将恢复后的结果保存到新文件，以保留原始结果作为备份

### 8. 无参考模式测试

无参考模式用于测试大语言模型是否在训练过程中已经记忆了小说内容。在此模式下，测试时不提供小说原文作为上下文，仅使用小说摘要作为背景信息，直接向模型提问。

#### 使用场景

- 检测模型是否在预训练时已经学习了《哈利·波特》小说内容
- 评估模型的"固有知识"与"上下文检索能力"的差异
- 作为基准对比，了解模型在有/无参考情况下的表现差异

#### 生成小说摘要

在使用无参考模式之前，需要先为问题集生成小说摘要。有两种方式：

**方式一：在生成问题时自动生成摘要**

```bash
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --generate-summary \
    --output data/questions.jsonl
```

**方式二：为已有问题集添加摘要**

```bash
python -m src.summary \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --output data/questions_with_summary.jsonl
```

#### 运行无参考测试

```bash
python -m src.test \
    --no-reference \
    --data_set data/questions_with_summary.jsonl \
    --output data/results_no_ref.jsonl
```

#### 参数说明

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--no-reference` | 是 | - | 启用无参考测试模式 |
| `--data_set` | 是 | - | 问题集 JSONL 文件路径（必须包含 `novel_summary` 元数据） |
| `--output` | 是 | - | 输出结果 JSONL 文件路径 |
| `--concurrency` | 否 | `5` | 并发测试请求数 |
| `--max-questions` | 否 | 全部 | 最大测试题目数量，按深度均匀采样 |
| `--skip-validation` | 否 | `false` | 跳过验证字段检查 |
| `--ignore-invalid` | 否 | `false` | 跳过无效问题而非报错 |

#### 注意事项

- `--no-reference` 不能与 `--novel`、`--context_length`、`--context-lengths`、`--depth-mode` 等参数同时使用
- 问题集必须包含 `novel_summary` 元数据字段，否则会报错
- 无参考模式会测试所有问题，不会根据位置过滤

#### 输出格式

无参考测试结果包含 `test_mode` 字段：

```json
{
  "question": "哈利使用了什么咒语？",
  "question_type": "single_choice",
  "choice": {"a": "除你武器", "b": "昏昏倒地", "c": "盔甲护身", "d": "呼神护卫"},
  "correct_answer": ["a"],
  "model_answer": ["a"],
  "parsing_status": "success",
  "position": {"start_pos": 12500, "end_pos": 12650},
  "score": 1.0,
  "metrics": {},
  "test_mode": "no_reference"
}
```

#### 摘要生成命令

独立的摘要生成工具用于为已有问题集添加小说摘要：

```bash
# 基本用法
python -m src.summary \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --output data/questions_with_summary.jsonl

# 自定义摘要行数（默认 100 行）
python -m src.summary \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --excerpt-lines 150 \
    --output data/questions_with_summary.jsonl
```

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `--novel` | 是 | - | 小说文本文件路径 |
| `--data_set` | 是 | - | 问题集 JSONL 文件路径 |
| `--output` | 否 | 覆盖原文件 | 输出文件路径 |
| `--excerpt-lines` | 否 | `100` | 用于生成摘要的小说行数 |

### 9. 生成深度热力图

生成二维热力图，展示不同上下文长度（X轴）和深度（Y轴）的准确率。

#### 基本用法

```bash
python -m src.heatmap \
    --mode depth \
    --results data/results_depth.jsonl \
    --output reports/depth_heatmap.html
```

#### 热力图坐标轴

- **X轴**：上下文长度（32K、64K、128K、200K 等）
- **Y轴**：证据深度（0%、25%、50%、75%、100%）
- **颜色**：准确率（绿色=高，红色=低，灰色=无数据）

## 项目结构

```
hogwarts-bench/
├── src/
│   ├── core/                      # 核心工具
│   │   ├── config.py              # 配置管理器
│   │   ├── llm_client.py          # 带重试逻辑的 LLM API 客户端
│   │   ├── tokenizer.py           # 分词工具（tiktoken）
│   │   ├── validator.py           # 问题验证
│   │   ├── prompt_template.py     # 提示词模板管理器
│   │   └── file_io.py             # 文件 I/O 工具
│   ├── generator/                 # 问题生成模块
│   │   ├── question_generator.py  # 主要生成逻辑
│   │   └── sampling.py            # 采样策略
│   ├── tester/                    # 测试模块
│   │   ├── testing_tool.py        # 主要测试逻辑
│   │   └── parser.py              # 带回退的答案解析
│   ├── reporter/                  # 报告生成模块
│   │   ├── report_generator.py    # 主要报告逻辑
│   │   ├── metrics.py             # 指标计算
│   │   └── visualization.py       # Plotly 可视化
│   ├── generate.py                # 问题生成器 CLI
│   ├── test.py                    # 测试工具 CLI
│   └── report.py                  # 报告生成器 CLI
├── prompts/                       # 提示词模板
│   ├── question_generation.json   # 问题生成模板
│   ├── testing.json               # 测试模板
│   └── README.md                  # 模板文档
├── tests/                         # 测试套件
│   ├── test_*.py                  # 单元测试和集成测试
│   └── fixtures/                  # 测试固件
├── data/                          # 数据目录（需创建）
│   ├── novels/                    # 放置小说文件
│   ├── questions/                 # 生成的问题集
│   └── results/                   # 测试结果
├── reports/                       # 生成的 HTML 报告（需创建）
├── .env.example                   # 示例配置
├── .env                           # 您的配置（需创建）
├── requirements.txt               # Python 依赖
├── setup.py                       # 包设置
└── README.md                      # 本文件
```

### 目录设置

创建数据和报告所需的目录：

```bash
mkdir -p data/novels data/questions data/results reports
```


## 自定义

### 提示词模板

Hogwarts-bench 使用可定制的 JSON 提示词模板进行问题生成和测试。您可以修改这些模板以适应不同的语言、领域或问题风格。

#### 模板位置

提示词模板存储在 `prompts/` 目录中：
- `prompts/question_generation.json`：问题生成模板
- `prompts/testing.json`：LLM 测试模板

#### 模板结构 

每个模板文件必须是有效的 JSON，具有以下结构：

```json
{
  "system": "设置上下文和角色的系统提示词",
  "user": "带有 {占位符} 的用户提示词，用于动态内容",
  "constraints": [
    "可选约束 1",
    "可选约束 2"
  ]
}
```

#### 可用占位符

**问题生成模板：**
- `{context}`：从小说中提取的文本上下文
- `{question_type}`：要生成的问题类型（如 "single_choice"、"multiple_choice"）

**测试模板：**
- `{context}`：用于回答问题的小说文本上下文
- `{question}`：问题文本
- `{choices}`：格式化的答案选项字符串

#### 自定义示例

要创建英文问题而非中文，修改 `prompts/question_generation.json`：

```json
{
  "system": "You are an expert at creating test questions. Generate structured test questions based on the provided context.",
  "user": "Based on the following text:\n\n{context}\n\nGenerate a {question_type} question.\n\nRequirements:\n1. The question should test detailed understanding and recall\n2. For single_choice: provide 4 options with 1 correct answer and 3 distractors\n3. For multiple_choice: provide 4 options with at least 2 correct answers and at least 2 distractors\n4. Output must be valid JSON in this format:\n{\n  \"question\": \"Question text\",\n  \"question_type\": \"single_choice or multiple_choice\",\n  \"choice\": {\n    \"a\": \"Option A\",\n    \"b\": \"Option B\",\n    \"c\": \"Option C\",\n    \"d\": \"Option D\"\n  },\n  \"answer\": [\"a\"]\n}\n\nOutput only the JSON, no additional text.",
  "constraints": [
    "Output must be valid JSON",
    "Multiple choice must have at least 2 distractors",
    "Answers must be valid choices"
  ]
}
```

#### 以编程方式加载自定义模板

```python
from src.core.prompt_template import PromptTemplateManager

# 从自定义目录加载模板
manager = PromptTemplateManager(template_dir="my_prompts/")

# 或加载特定的自定义模板
manager.load_custom_template(
    "path/to/custom_template.json",
    template_type="question_generation"
)
```

更多详情请参阅 `prompts/README.md`。

### 采样策略

提供两种采样策略：

- **分层采样**（默认）：将小说分成 50k token 的层，并从每层均匀采样。这确保了对整部小说的全面覆盖，推荐用于大多数用例。

- **随机采样**：在整部小说中随机采样位置。适用于无偏测试，但可能导致不同文本区域的覆盖不均匀。

您可以在生成问题时使用 `--sampling_strategy` 参数指定策略。

## 故障排除

### 常见问题及解决方案

#### API 速率限制

**问题：** 从 API 提供商收到速率限制错误。

**解决方案：**
1. 降低 `--concurrency` 参数（尝试 `--concurrency 3` 或 `--concurrency 1`）
2. 在 `.env` 文件中增加 `DEFAULT_RETRY_TIMES` 以允许更多重试
3. 通过降低并发来增加请求之间的延迟
4. 检查您的 API 提供商的速率限制并相应调整

```bash
# 示例：为速率受限的 API 降低并发
python -m src.generate \
    --novel data/novel.txt \
    --question_nums 100 \
    --concurrency 2 \
    --retry_times 5 \
    --output data/questions.jsonl
```

#### 超时错误

**问题：** 请求在完成前超时。

**解决方案：**
1. 在 `.env` 文件中增加 `DEFAULT_TIMEOUT`（如 `DEFAULT_TIMEOUT=120`）
2. 如果响应太长，减少 `DEFAULT_MAX_TOKENS`
3. 检查您的网络连接和 API 端点状态
4. 对于非常慢的端点，考虑使用不同的模型或提供商

```bash
# 在 .env 文件中
DEFAULT_TIMEOUT=120
DEFAULT_MAX_TOKENS=1500
```

#### 内存问题

**问题：** 处理大型小说时内存不足。

**解决方案：**
1. 测试时减少 `--context_length`（如使用 32000 而非 128000）
2. 分批处理问题
3. 减少 `--concurrency` 以限制同时操作
4. 关闭其他内存密集型应用程序

```bash
# 示例：使用较小的上下文长度测试
python -m src.test \
    --novel data/large_novel.txt \
    --data_set data/questions.jsonl \
    --context_length 32000 \
    --concurrency 3 \
    --output data/results.jsonl
```

#### 无效的 JSON 响应

**问题：** LLM 返回无法解析为 JSON 的响应。

**解决方案：**
1. 框架包含回退解析策略（正则表达式提取）
2. 检查您的提示词模板以确保它们明确请求 JSON 输出
3. 尝试更好遵循 JSON 格式指令的不同模型
4. 查看结果中的 `parsing_status` 字段以识别有问题的响应
5. 如果响应太僵硬，稍微增加 `DEFAULT_TEMPERATURE`；如果太有创意，则降低

#### 文件丢失或损坏

**问题：** 加载小说、问题集或结果文件时出错。

**解决方案：**
1. 验证文件路径正确且文件存在
2. 确保文件是 UTF-8 编码（特别是非英文文本）
3. 检查 JSONL 文件每行都是有效的 JSON
4. 验证您对目录有读/写权限

```bash
# 检查文件编码（Linux/Mac）
file -i data/novel.txt

# 如需要转换为 UTF-8（Linux/Mac）
iconv -f GBK -t UTF-8 data/novel.txt > data/novel_utf8.txt
```

#### API 认证错误

**问题：** 从 API 收到 401 或 403 错误。

**解决方案：**
1. 验证 `.env` 文件中的 `OPENAI_API_KEY` 是否正确
2. 检查您的 API 密钥是否有足够的额度/配额
3. 确保 `OPENAI_BASE_URL` 与您的 API 提供商匹配
4. 对于 OpenRouter，验证您的密钥来自 https://openrouter.ai/keys
5. 对于 OpenAI，使用 `OPENAI_BASE_URL=https://api.openai.com/v1`

```bash
# OpenAI 的 .env 示例
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4-turbo-preview

# OpenRouter 的 .env 示例
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=anthropic/claude-3-sonnet
```

#### 问题未生成

**问题：** 问题生成完成但产生的问题很少或没有。

**解决方案：**
1. 检查日志中的验证错误
2. 验证您的提示词模板请求正确的 JSON 格式
3. 尝试增加 `--retry_times` 以允许更多尝试
4. 先用较小的 `--question_nums` 测试以进行调试
5. 查看 LLM 的原始响应以确认是否符合预期格式

#### 测试性能差

**问题：** LLM 在测试中表现不佳。

**解决方案：**
1. 验证 `--context_length` 足以包含答案位置
2. 检查 `--padding_size` 是否提供足够的缓冲（默认 500 tokens）
3. 确保小说文本干净且格式正确
4. 尝试可能具有更好长上下文能力的不同模型
5. 查看 HTML 报告中的错误案例以识别模式

#### 报告生成失败

**问题：** 无法从结果生成 HTML 报告。

**解决方案：**
1. 验证结果 JSONL 文件有效且未损坏
2. 检查您对输出目录有写权限
3. 确保所有必需的依赖已安装（`pip install -r requirements.txt`）
4. 如果错误采样有问题，尝试减少 `--error_examples`
5. 检查控制台输出以获取具体错误信息

### 获取帮助

如果您遇到此处未涵盖的问题：

1. 检查控制台输出以获取详细错误信息
2. 查看设计文档（`.kiro/specs/hogwarts-bench/design.md`）了解技术细节
3. 验证您的环境满足前置条件（Python 3.8+）
4. 先尝试使用最小示例运行以隔离问题
5. 在项目仓库中提交 issue，包含：
   - 错误信息和堆栈跟踪
   - 您运行的命令
   - Python 版本和操作系统
   - 相关配置（不含 API 密钥）


## 高级用法

### 测试多个上下文长度

要评估性能如何随上下文长度变化，使用不同的 `--context_length` 值运行测试：

```bash
# 在不同上下文长度下测试
for length in 8000 16000 32000 64000 128000; do
    python -m src.test \
        --novel data/harry_potter_1.txt \
        --data_set data/questions.jsonl \
        --context_length $length \
        --output data/results_${length}.jsonl
    
    python -m src.report \
        --results data/results_${length}.jsonl \
        --output reports/report_${length}.html
done
```

### 批量处理多部小说

批量处理多部小说：

```bash
# 为多部小说生成问题
for novel in data/novels/*.txt; do
    basename=$(basename "$novel" .txt)
    python -m src.generate \
        --novel "$novel" \
        --question_nums 200 \
        --output "data/questions_${basename}.jsonl"
done
```

### 使用不同模型

通过更改 `.env` 文件中的 `MODEL_NAME` 来使用不同模型测试相同的问题集：

```bash
# 使用 Claude 测试
MODEL_NAME=anthropic/claude-3-sonnet python -m src.test \
    --novel data/novel.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results_claude.jsonl

# 使用 GPT-4 测试
MODEL_NAME=openai/gpt-4-turbo python -m src.test \
    --novel data/novel.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results_gpt4.jsonl
```

## 性能提示

1. **优化并发**：从低并发（2-3）开始，根据您的 API 速率限制逐渐增加
2. **使用分层采样**：为了全面评估，分层采样确保覆盖整部小说
3. **适当的上下文窗口**：使用 500-1000 tokens 进行问题生成以提供足够的上下文
4. **填充大小**：保持填充在 500+ tokens 以确保答案不会在上下文边界被截断
5. **批量大小**：一次生成 50-100 个问题以便于调试和迭代

## 数据格式规范

### 问题集格式（JSONL）

问题集文件中的每行是一个 JSON 对象：

```json
{
  "question": "问题文本",
  "question_type": "single_choice",
  "choice": {
    "a": "选项A",
    "b": "选项B", 
    "c": "选项C",
    "d": "选项D"
  },
  "answer": ["a"],
  "position": {
    "start_pos": 12500,
    "end_pos": 12650
  }
}
```

### 测试结果格式（JSONL）

结果文件中的每行是一个 JSON 对象：

```json
{
  "question": "问题文本",
  "question_type": "single_choice",
  "choice": {"a": "选项A", "b": "选项B", "c": "选项C", "d": "选项D"},
  "correct_answer": ["a"],
  "model_answer": ["a"],
  "parsing_status": "success",
  "position": {"start_pos": 12500, "end_pos": 12650},
  "score": 1.0,
  "metrics": {
    "precision": 1.0,
    "recall": 1.0,
    "f1_score": 1.0
  }
}
```

## 指标说明

### 单选题

- **准确率**：正确回答的问题百分比（精确匹配）

### 多选题

- **精确率**：在模型选择的选项中，有多少百分比是正确的？
- **召回率**：在正确选项中，模型选择了多少百分比？
- **F1 分数**：精确率和召回率的调和平均值（平衡指标）

### 总体指标

- **宏平均**：所有问题指标的平均值（平等对待每个问题）
- **解析成功率**：成功解析为 JSON 的响应百分比
- **拒绝率**：模型拒绝回答的问题百分比

## 系统要求

- Python 3.8 或更高版本
- pip 包管理器
- 用于 API 调用的互联网连接
- 来自 OpenAI、OpenRouter 或兼容提供商的 API 密钥

## 依赖项

主要依赖项（完整列表见 `requirements.txt`）：

- `openai>=1.0.0` - LLM API 客户端
- `tiktoken>=0.5.0` - 分词
- `plotly>=5.0.0` - 交互式可视化
- `python-dotenv>=1.0.0` - 环境配置
- `aiohttp>=3.9.0` - 异步 HTTP 请求

## 许可证

MIT 许可证

## 贡献

欢迎贡献！请提交 issue 或 pull request。

### 开发设置

```bash
# 克隆仓库
git clone <repository-url>
cd hogwarts-bench

# 以开发模式安装
pip install -e .

# 运行测试
pytest tests/
```

## 引用

如果您在研究中使用 Hogwarts-bench，请引用：

```bibtex
@software{hogwarts_bench,
  title={Hogwarts-bench: A Long-Context Evaluation Framework for LLMs},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/hogwarts-bench}
}
```
