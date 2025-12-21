# 设计文档

## 概述

Hogwarts-bench 是一个基于 Python 的自动化测试框架，用于评估 LLM 的长文本能力。系统采用管道架构，包含三个独立的 CLI 工具，可以按顺序执行或单独运行。每个工具读取和写入标准化的文件格式（JSONL、JSON、HTML），以确保模块化和可扩展性。

该框架利用 OpenAI Python SDK 进行 LLM 交互，使用 tiktoken 进行分词，使用 Plotly 进行交互式可视化。所有配置通过环境变量和命令行参数管理，并提供合理的默认值以最小化设置难度。

## 架构

### 系统组件

```
┌─────────────────────────────────────────────────────────────┐
│                     Hogwarts-Bench                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  题目生成器      │      │  测试工具        │           │
│  │  (generate.py)   │─────▶│  (test.py)       │           │
│  └──────────────────┘      └──────────────────┘           │
│         │                           │                      │
│         │ questions.jsonl           │ results.jsonl        │
│         ▼                           ▼                      │
│  ┌──────────────────────────────────────────────┐         │
│  │         报告生成器                           │         │
│  │         (report.py)                          │         │
│  └──────────────────────────────────────────────┘         │
│                      │                                     │
│                      ▼                                     │
│              report.html                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  共享组件                                   │
├─────────────────────────────────────────────────────────────┤
│  • 配置管理器    • LLM 客户端    • 分词器                  │
│  • 提示词模板    • 验证器        • 文件 I/O 工具           │
└─────────────────────────────────────────────────────────────┘
```

### 模块职责

**题目生成器 (`generate.py`)**
- 读取小说文本并应用采样策略
- 通过 LLM 生成带上下文窗口的题目
- 验证并保存结构化题目集

**测试工具 (`test.py`)**
- 加载题目并准备测试上下文
- 使用并发请求在目标 LLM 上执行测试
- 解析响应并保存结构化结果

**报告生成器 (`report.py`)**
- 分析测试结果并计算指标
- 生成带可视化的交互式 HTML 报告
- 提供错误案例分析

## 组件和接口

### 1. 配置管理器

**目的：** 集中式配置加载和验证

**接口：**
```python
class Config:
    @staticmethod
    def load_from_env() -> dict:
        """从 .env 文件加载配置"""
        
    @staticmethod
    def validate_config(config: dict) -> bool:
        """验证必需的配置参数"""
        
    @staticmethod
    def get_llm_config() -> dict:
        """返回 LLM 特定配置"""
```

**配置模式：**
```python
{
    "api_key": str,           # LLM API 密钥
    "base_url": str,          # API 端点（默认：OpenRouter）
    "model_name": str,        # 模型标识符
    "temperature": float,     # 生成温度（默认：0.7）
    "max_tokens": int,        # 最大响应 token 数（默认：2000）
    "timeout": int            # 请求超时秒数（默认：60）
}
```

### 2. LLM 客户端

**目的：** 带重试逻辑的 LLM API 调用统一接口

**接口：**
```python
class LLMClient:
    def __init__(self, config: dict):
        """使用配置初始化 OpenAI 客户端"""
        
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """从 LLM 生成响应"""
        
    async def generate_batch(self, prompts: list[str], 
                            concurrency: int = 5) -> list[str]:
        """并发生成响应"""
        
    def _retry_with_backoff(self, func, max_retries: int = 3):
        """使用指数退避重试失败的请求"""
```

**错误处理：**
- 网络错误：使用指数退避重试
- 速率限制错误：等待并重试
- 超时错误：达到最大重试次数后记录并跳过
- 无效响应：返回 None 并记录

### 3. 分词器

**目的：** 所有模块间的一致分词

**接口：**
```python
class Tokenizer:
    def __init__(self, encoding_name: str = "cl100k_base"):
        """初始化 tiktoken 编码器"""
        
    def encode(self, text: str) -> list[int]:
        """将文本转换为 token ID"""
        
    def decode(self, tokens: list[int]) -> str:
        """将 token ID 转换为文本"""
        
    def count_tokens(self, text: str) -> int:
        """计算文本中的 token 数"""
        
    def find_sentence_boundary(self, text: str, 
                              target_pos: int, 
                              direction: str = "forward") -> int:
        """从目标位置查找最近的句子边界"""
```

**边界检测：**
- 使用正则表达式识别句子结尾：`.!?` 后跟空格或换行
- 对于段落边界：查找双换行符 `\n\n`
- 如果在 100 个 token 内未找到边界，使用硬截断

### 4. 提示词模板管理器

**目的：** 加载和管理可自定义的提示词模板

**接口：**
```python
class PromptTemplateManager:
    def __init__(self, template_dir: str = "prompts/"):
        """从目录加载模板"""
        
    def get_question_generation_prompt(self, 
                                      context: str, 
                                      question_type: str) -> str:
        """获取题目生成提示词"""
        
    def get_testing_prompt(self, context: str, question: dict) -> str:
        """获取模型测试提示词"""
        
    def load_custom_template(self, template_path: str):
        """加载用户提供的模板"""
```

**模板格式：**
模板存储为带占位符的 JSON 文件：
```json
{
    "system": "你是一个创建测试题的专家...",
    "user": "基于以下上下文：\n\n{context}\n\n生成一个 {question_type} 题目...",
    "constraints": [
        "输出必须是有效的 JSON",
        "多选题至少包含 2 个干扰选项"
    ]
}
```

### 5. 题目生成器核心

**目的：** 题目生成的主要逻辑

**接口：**
```python
class QuestionGenerator:
    def __init__(self, config: dict, llm_client: LLMClient):
        """使用配置和 LLM 客户端初始化"""
        
    def generate_questions(self, 
                          novel_path: str,
                          num_questions: int,
                          sampling_strategy: str = "stratified",
                          context_window_size: int = 500,
                          concurrency: int = 5) -> list[dict]:
        """题目生成的主入口点"""
        
    def _sample_positions(self, 
                         total_tokens: int,
                         num_samples: int,
                         strategy: str) -> list[int]:
        """基于策略采样位置"""
        
    def _extract_context(self, 
                        tokens: list[int],
                        position: int,
                        window_size: int) -> tuple[list[int], int, int]:
        """提取带边界对齐的上下文窗口"""
        
    async def _generate_single_question(self, 
                                       context: str,
                                       position: int) -> dict:
        """从上下文生成一个题目"""
        
    def _validate_question(self, question: dict) -> bool:
        """验证题目结构和内容"""
```

**采样策略实现：**

*分层采样：*
```python
def _stratified_sample(total_tokens: int, num_samples: int) -> list[int]:
    layer_size = 50000  # 每层的 token 数
    num_layers = ceil(total_tokens / layer_size)
    samples_per_layer = num_samples // num_layers
    
    positions = []
    for layer_idx in range(num_layers):
        layer_start = layer_idx * layer_size
        layer_end = min((layer_idx + 1) * layer_size, total_tokens)
        
        # 在层内均匀采样
        for _ in range(samples_per_layer):
            pos = random.randint(layer_start, layer_end - 1)
            positions.append(pos)
    
    return sorted(positions)
```

*随机采样：*
```python
def _random_sample(total_tokens: int, num_samples: int) -> list[int]:
    return sorted(random.sample(range(total_tokens), num_samples))
```

### 6. 题目验证器

**目的：** 验证生成的题目符合质量标准

**接口：**
```python
class QuestionValidator:
    @staticmethod
    def validate_structure(question: dict) -> tuple[bool, str]:
        """验证 JSON 结构"""
        
    @staticmethod
    def validate_content(question: dict) -> tuple[bool, str]:
        """验证内容质量"""
        
    @staticmethod
    def validate_answer_choices(question: dict) -> tuple[bool, str]:
        """验证答案是有效选项"""
```

**验证规则：**
1. 必需字段：question、question_type、choice、answer、position
2. question_type 必须是：single_choice、multiple_choice、negative_question 之一
3. choice 必须是至少包含 2 个选项的字典
4. answer 必须是有效选项键的列表
5. position 必须有 start_pos 和 end_pos 整数
6. 对于 multiple_choice：至少 2 个干扰选项（总数 - 正确数 >= 2）

### 7. 测试工具核心

**目的：** 在目标 LLM 上执行测试

**接口：**
```python
class TestingTool:
    def __init__(self, config: dict, llm_client: LLMClient):
        """使用配置和 LLM 客户端初始化"""
        
    def run_tests(self,
                 novel_path: str,
                 question_set_path: str,
                 context_length: int,
                 padding_size: int = 500,
                 concurrency: int = 5) -> list[dict]:
        """测试的主入口点"""
        
    def _prepare_context(self, 
                        novel_tokens: list[int],
                        context_length: int) -> str:
        """提取前 N 个 token 作为上下文"""
        
    def _filter_questions(self,
                         questions: list[dict],
                         context_length: int,
                         padding_size: int) -> list[dict]:
        """过滤适合上下文的题目"""
        
    async def _test_single_question(self,
                                   context: str,
                                   question: dict) -> dict:
        """测试一个题目"""
        
    def _parse_answer(self, response: str) -> tuple[list[str], str]:
        """使用回退策略解析 LLM 响应"""
```

**答案解析策略：**
```python
def _parse_answer(response: str) -> tuple[list[str], str]:
    # 策略 1：直接 JSON 解析
    try:
        data = json.loads(response)
        return data.get("answer", []), "success"
    except json.JSONDecodeError:
        pass
    
    # 策略 2：正则提取
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return data.get("answer", []), "regex_extracted"
        except json.JSONDecodeError:
            pass
    
    # 策略 3：解析失败
    return [], "parsing_error"
```

### 8. 报告生成器核心

**目的：** 分析结果并生成 HTML 报告

**接口：**
```python
class ReportGenerator:
    def __init__(self, results_path: str):
        """加载测试结果"""
        
    def generate_report(self, output_path: str):
        """生成完整的 HTML 报告"""
        
    def _calculate_metrics(self) -> dict:
        """计算所有性能指标"""
        
    def _generate_summary_section(self) -> str:
        """生成摘要部分的 HTML"""
        
    def _generate_scatter_plot(self) -> str:
        """生成 Plotly 散点图 HTML"""
        
    def _generate_error_analysis(self, num_examples: int = 10) -> str:
        """生成错误案例分析 HTML"""
```

**指标计算：**

*单选题准确率：*
```python
def calculate_accuracy(results: list[dict]) -> float:
    correct = sum(1 for r in results 
                  if r["question_type"] == "single_choice" 
                  and r["model_answer"] == r["correct_answer"])
    total = sum(1 for r in results 
                if r["question_type"] == "single_choice")
    return correct / total if total > 0 else 0.0
```

*多选题指标：*
```python
def calculate_multi_choice_metrics(results: list[dict]) -> dict:
    precisions, recalls, f1_scores = [], [], []
    
    for result in results:
        if result["question_type"] != "multiple_choice":
            continue
            
        correct = set(result["correct_answer"])
        predicted = set(result["model_answer"])
        
        if len(predicted) == 0:
            precision = 0.0
        else:
            precision = len(correct & predicted) / len(predicted)
            
        if len(correct) == 0:
            recall = 0.0
        else:
            recall = len(correct & predicted) / len(correct)
            
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)
            
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
    
    return {
        "avg_precision": sum(precisions) / len(precisions) if precisions else 0.0,
        "avg_recall": sum(recalls) / len(recalls) if recalls else 0.0,
        "avg_f1": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    }
```

### 9. 可视化生成器

**目的：** 创建交互式 Plotly 可视化

**接口：**
```python
class VisualizationGenerator:
    def create_scatter_plot(self, 
                           results: list[dict],
                           context_length: int) -> str:
        """创建带趋势线的散点图"""
        
    def _assign_colors(self, result: dict) -> str:
        """根据正确性分配颜色"""
        
    def _calculate_trend_line(self, 
                             positions: list[int],
                             scores: list[float]) -> tuple[list[int], list[float]]:
        """计算平滑趋势线"""
```

**散点图规格：**
- X 轴：Token 位置（0 到 context_length）
- Y 轴：性能分数（0.0 到 1.0）
- 点颜色：
  - 绿色 (#28a745)：分数 == 1.0
  - 黄色 (#ffc107)：0.0 < 分数 < 1.0
  - 红色 (#dc3545)：分数 == 0.0
  - 灰色 (#6c757d)：parsing_error 或 refused
- 悬停信息：题目文本（截断）、正确答案、模型答案、分数
- 趋势线：窗口大小 = 20 点的移动平均

## 数据模型

### 题目模式

```python
{
    "question": str,              # 题目文本
    "question_type": str,         # "single_choice" | "multiple_choice" | "negative_question"
    "choice": {                   # 答案选项
        "a": str,
        "b": str,
        "c": str,
        "d": str
    },
    "answer": list[str],          # 正确答案，例如 ["a"] 或 ["a", "c"]
    "position": {                 # 答案在小说中的位置
        "start_pos": int,         # 起始 token 位置
        "end_pos": int            # 结束 token 位置
    }
}
```

### 题目集元数据模式

```python
{
    "metadata": {
        "generated_at": str,      # ISO 时间戳
        "model_name": str,        # 用于生成的模型
        "novel_path": str,        # 源小说文件
        "total_questions": int,   # 题目数量
        "sampling_strategy": str, # 使用的采样方法
        "context_window_size": int,
        "config": dict            # 完整生成配置
    },
    "questions": list[Question]   # 题目对象列表
}
```

### 测试结果模式

```python
{
    "question": str,              # 原始题目
    "question_type": str,         # 题目类型
    "choice": dict,               # 答案选项
    "correct_answer": list[str],  # 正确答案
    "model_answer": list[str],    # 模型的答案
    "parsing_status": str,        # "success" | "regex_extracted" | "parsing_error"
    "position": dict,             # 答案位置
    "score": float,               # 0.0 到 1.0（准确率或 F1）
    "metrics": {                  # 仅用于多选题
        "precision": float,
        "recall": float,
        "f1_score": float
    }
}
```

### 测试结果文件模式

```python
{
    "metadata": {
        "tested_at": str,         # ISO 时间戳
        "model_name": str,        # 测试的模型
        "novel_path": str,        # 源小说
        "question_set_path": str, # 使用的题目集
        "context_length": int,    # 使用的上下文长度
        "padding_size": int,      # 使用的填充大小
        "total_questions": int,   # 题目集中的题目数
        "tested_questions": int,  # 实际测试的题目数
        "config": dict            # 完整测试配置
    },
    "results": list[TestResult]   # 结果对象列表
}
```

## 错误处理

### 题目生成错误

| 错误类型 | 处理策略 |
|---------|---------|
| LLM API 超时 | 重试最多 retry_times 次，然后跳过题目 |
| 无效 JSON 响应 | 记录错误，重试最多 retry_times 次，然后跳过 |
| 验证失败 | 记录验证错误，使用修改后的提示词重试 |
| 超过速率限制 | 使用指数退避等待，然后重试 |
| 网络错误 | 使用指数退避重试最多 retry_times 次 |

### 测试错误

| 错误类型 | 处理策略 |
|---------|---------|
| LLM API 超时 | 重试最多 retry_times 次，标记为 "timeout" |
| 解析失败 | 应用回退策略，标记为 "parsing_error" |
| 模型拒绝 | 标记为 "refused"，包含在报告中 |
| 上下文过长 | 跳过题目，记录警告 |
| 网络错误 | 使用指数退避重试 |

### 报告生成错误

| 错误类型 | 处理策略 |
|---------|---------|
| 缺少结果文件 | 退出并显示清晰的错误消息 |
| 损坏的结果数据 | 跳过损坏的条目，记录警告 |
| 可视化失败 | 生成不带可视化的报告，记录错误 |
| 文件写入错误 | 退出并显示错误消息和建议的修复方法 |

## 测试策略

### 单元测试

**要测试的核心组件：**
1. 分词器边界检测
2. 题目验证器逻辑
3. 各种格式的答案解析器
4. 指标计算函数
5. 采样策略实现

**测试方法：**
- 使用 pytest 框架
- 使用预定义响应模拟 LLM API 调用
- 测试边缘情况（空输入、格式错误的数据、边界条件）
- 验证错误处理路径

### 集成测试

**要测试的场景：**
1. 使用模拟 LLM 的端到端题目生成
2. 使用模拟 LLM 响应的端到端测试
3. 从样本结果生成报告
4. 配置加载和验证
5. 文件 I/O 操作

**测试数据：**
- 小样本小说（1000 个 token）
- 预生成的题目集
- 模拟 LLM 响应（有效、无效、边缘情况）

### 手动测试

**验证步骤：**
1. 从《哈利·波特》样本章节生成题目
2. 验证题目质量和多样性
3. 在真实 LLM 上运行测试（例如 GPT-3.5）
4. 检查生成的 HTML 报告的正确性
5. 测试报告中的交互功能（悬停、缩放）

## 项目结构

```
hogwarts-bench/
├── src/
│   ├── __init__.py
│   ├── generate.py              # 题目生成器 CLI
│   ├── test.py                  # 测试工具 CLI
│   ├── report.py                # 报告生成器 CLI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # 配置管理器
│   │   ├── llm_client.py        # LLM 客户端包装器
│   │   ├── tokenizer.py         # 分词工具
│   │   ├── validator.py         # 题目验证器
│   │   └── file_io.py           # 文件 I/O 工具
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── question_generator.py
│   │   └── sampling.py          # 采样策略
│   ├── tester/
│   │   ├── __init__.py
│   │   ├── testing_tool.py
│   │   └── parser.py            # 答案解析器
│   └── reporter/
│       ├── __init__.py
│       ├── report_generator.py
│       ├── metrics.py           # 指标计算
│       └── visualization.py     # Plotly 可视化
├── prompts/
│   ├── question_generation.json # 默认生成提示词
│   └── testing.json             # 默认测试提示词
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── data/                        # 样本数据和输出
├── .env.example                 # 示例配置
├── requirements.txt
├── README.md
└── setup.py
```

## 依赖项

```
openai>=1.0.0              # LLM API 客户端
tiktoken>=0.5.0            # 分词
plotly>=5.0.0              # 交互式可视化
python-dotenv>=1.0.0       # 环境配置
aiohttp>=3.9.0             # 异步 HTTP 请求
pytest>=7.0.0              # 测试框架
pytest-asyncio>=0.21.0     # 异步测试支持
```

## 配置示例

### .env 文件

```bash
# LLM 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=anthropic/claude-3-sonnet

# 生成设置
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000
DEFAULT_TIMEOUT=60

# 并发设置
DEFAULT_CONCURRENCY=5
DEFAULT_RETRY_TIMES=3
```

### 命令行使用

```bash
# 生成题目
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --sampling_strategy stratified \
    --context_window_size 500 \
    --concurrency 10 \
    --retry_times 3 \
    --output data/questions.jsonl

# 运行测试
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --padding_size 500 \
    --concurrency 5 \
    --output data/results.jsonl

# 生成报告
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html \
    --error_examples 15
```
