# Design Document

## Overview

本设计文档描述深度感知测试（Depth-Aware Testing）功能的技术实现方案。该功能通过动态构建上下文，将答案放置在不同深度位置，全面评估 LLM 的长上下文召回能力。

核心思想是：对于每个测试问题，不再简单地取小说前 N 个 token，而是根据目标深度动态构建上下文：
- 从小说中提取包含答案的证据段落
- 用小说其他部分的文本作为前缀和后缀填充
- 通过调整前缀长度来控制答案在上下文中的深度位置

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│  src/test.py (扩展参数)    src/heatmap.py (新增 depth 模式)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Testing Tool Layer                          │
│  src/tester/testing_tool.py (扩展深度感知测试逻辑)               │
│  src/tester/context_builder.py (新增：上下文构建器)              │
│  src/tester/depth_scheduler.py (新增：深度调度器)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Visualization Layer                          │
│  src/reporter/heatmap.py (扩展深度热力图)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. ContextBuilder (新增组件)

**文件**: `src/tester/context_builder.py`

**职责**: 根据目标深度动态构建测试上下文

```python
@dataclass
class ContextBuildResult:
    """上下文构建结果"""
    context: str                    # 构建的上下文文本
    actual_depth: float             # 实际深度 (0.0-1.0)
    evidence_start: int             # 证据在上下文中的起始位置（token）
    evidence_end: int               # 证据在上下文中的结束位置（token）
    prefix_length: int              # 前缀长度（token）
    suffix_length: int              # 后缀长度（token）
    success: bool                   # 是否构建成功
    error_message: Optional[str]    # 错误信息（如果失败）


class ContextBuilder:
    """上下文构建器"""
    
    def __init__(self, tokenizer: Tokenizer, novel_tokens: List[int]):
        """
        初始化上下文构建器
        
        Args:
            tokenizer: 分词器实例
            novel_tokens: 完整小说的 token 列表
        """
        pass
    
    def build_context(
        self,
        question: Dict[str, Any],
        target_depth: float,
        context_length: int,
        padding_size: int = 500
    ) -> ContextBuildResult:
        """
        为问题构建指定深度的上下文
        
        Args:
            question: 问题字典，包含 position 信息
            target_depth: 目标深度 (0.0=开头, 0.5=中间, 1.0=结尾)
            context_length: 目标上下文长度（token）
            padding_size: 证据段落前后的安全边距（token）
            
        Returns:
            ContextBuildResult 包含构建结果
        """
        pass
    
    def _extract_evidence(
        self, 
        start_pos: int, 
        end_pos: int, 
        padding: int
    ) -> Tuple[List[int], int, int]:
        """
        提取证据段落（包含前后 padding）
        
        Returns:
            (evidence_tokens, actual_start, actual_end)
        """
        pass
    
    def _get_filler_tokens(
        self, 
        length: int, 
        exclude_start: int, 
        exclude_end: int
    ) -> List[int]:
        """
        获取填充文本（排除证据区域）
        
        从小说中随机选取不包含证据的连续文本段落
        """
        pass
```

### 2. DepthScheduler (新增组件)

**文件**: `src/tester/depth_scheduler.py`

**职责**: 为问题分配测试深度

```python
class DepthMode(Enum):
    """深度模式枚举"""
    LEGACY = "legacy"       # 传统模式，不使用深度感知
    UNIFORM = "uniform"     # 均匀分配到 5 个深度区间
    FIXED = "fixed"         # 固定深度


@dataclass
class DepthAssignment:
    """深度分配结果"""
    question_index: int
    target_depth: float
    depth_bin: str          # "0%", "25%", "50%", "75%", "100%"
    context_length: int


class DepthScheduler:
    """深度调度器"""
    
    DEPTH_BINS = [0.0, 0.25, 0.50, 0.75, 1.0]
    DEPTH_LABELS = ["0%", "25%", "50%", "75%", "100%"]
    
    def __init__(
        self,
        mode: DepthMode,
        fixed_depth: Optional[float] = None,
        context_lengths: Optional[List[int]] = None
    ):
        """
        初始化深度调度器
        
        Args:
            mode: 深度模式
            fixed_depth: 固定深度值（仅 FIXED 模式使用）
            context_lengths: 上下文长度列表（多长度测试）
        """
        pass
    
    def schedule(
        self, 
        questions: List[Dict[str, Any]]
    ) -> List[DepthAssignment]:
        """
        为问题列表分配深度
        
        Args:
            questions: 问题列表
            
        Returns:
            深度分配列表
        """
        pass
    
    def _schedule_uniform(
        self, 
        questions: List[Dict], 
        context_lengths: List[int]
    ) -> List[DepthAssignment]:
        """均匀分配策略"""
        pass
    
    def _schedule_fixed(
        self, 
        questions: List[Dict], 
        context_lengths: List[int]
    ) -> List[DepthAssignment]:
        """固定深度策略"""
        pass
```

### 3. TestingTool 扩展

**文件**: `src/tester/testing_tool.py`

**修改**: 添加深度感知测试支持

```python
class TestingTool:
    # 新增方法
    async def run_depth_aware_tests(
        self,
        novel_path: str,
        question_set_path: str,
        depth_mode: str,                    # "legacy", "uniform", "fixed"
        context_lengths: List[int],         # 支持多个上下文长度
        fixed_depth: Optional[float] = None,
        padding_size: int = 500,
        concurrency: int = 5,
        output_path: Optional[str] = None,
        skip_validation: bool = False,
        ignore_invalid: bool = False
    ) -> List[Dict[str, Any]]:
        """
        执行深度感知测试
        
        与 run_tests 的区别：
        1. 使用 ContextBuilder 动态构建上下文
        2. 使用 DepthScheduler 分配测试深度
        3. 结果中包含 depth 和 depth_bin 字段
        """
        pass
```

### 4. 热力图扩展

**文件**: `src/reporter/heatmap.py`

**热力图坐标轴设计**:
- 横轴（X轴）：上下文长度（如 32K、64K、128K、200K）
- 纵轴（Y轴）：答案深度（0%、25%、50%、75%、100%）
- 颜色：准确率（绿色=高，红色=低，灰色=无数据）

**新增函数**:

```python
@dataclass
class DepthBinStats:
    """深度区间统计"""
    context_length: int
    depth_bin: str          # "0%", "25%", "50%", "75%", "100%"
    accuracy: Optional[float]
    question_count: int


def calculate_depth_bins(
    results: List[ResultEntry],
    context_lengths: List[int],
    depth_labels: List[str] = ["0%", "25%", "50%", "75%", "100%"]
) -> List[DepthBinStats]:
    """
    计算深度热力图的统计数据
    
    Args:
        results: 测试结果列表（需包含 depth_bin 和 context_length 字段）
        context_lengths: 上下文长度列表
        depth_labels: 深度标签列表
        
    Returns:
        每个 (context_length, depth_bin) 组合的统计数据
    """
    pass


def create_depth_heatmap(
    bins: List[DepthBinStats],
    metadata: Optional[DatasetMetadata] = None
) -> str:
    """
    创建二维深度热力图
    
    Args:
        bins: 深度区间统计数据
        metadata: 数据集元信息
        
    Returns:
        Plotly HTML 字符串
    """
    pass
```

## Data Models

### 扩展的测试结果格式

```json
{
    "question": "问题文本",
    "question_type": "single_choice",
    "choice": {"a": "...", "b": "...", "c": "...", "d": "..."},
    "correct_answer": ["b"],
    "model_answer": ["b"],
    "parsing_status": "success",
    "position": {"start_pos": 1389, "end_pos": 1889},
    "score": 1.0,
    "metrics": {},
    
    // 新增字段（深度感知模式）
    "depth": 0.5,                    // 实际测试深度 (0.0-1.0)
    "depth_bin": "50%",              // 深度区间标签
    "test_context_length": 128000   // 实际使用的上下文长度
}
```

### 扩展的 Metadata 格式

```json
{
    "metadata": {
        "tested_at": "2024-01-01T12:00:00",
        "model_name": "gpt-4",
        "novel_path": "data/harry_potter_5.txt",
        "question_set_path": "data/questions.jsonl",
        
        // 新增字段
        "depth_mode": "uniform",
        "context_lengths": [32000, 64000, 128000, 200000],
        "depth_bins": ["0%", "25%", "50%", "75%", "100%"],
        "questions_per_bin": 10
    }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 上下文长度一致性

*For any* 构建请求，如果构建成功，则生成的上下文 token 数量应等于指定的 context_length（允许 ±1% 误差）

**Validates: Requirements 1.7**

### Property 2: 深度位置准确性

*For any* 目标深度 d，构建的上下文中证据段落的实际深度应在 d ± 5% 范围内

**Validates: Requirements 1.2, 1.3, 1.4**

### Property 3: 证据完整性

*For any* 成功构建的上下文，原始证据段落应完整包含在上下文中，不被截断

**Validates: Requirements 1.1, 1.5**

### Property 4: 均匀分配平衡性

*For any* uniform 模式的深度分配，每个深度区间分配的问题数量差异不超过 1

**Validates: Requirements 2.1**

### Property 5: 结果字段完整性

*For any* 深度感知模式的测试结果，必须包含 depth、depth_bin、test_context_length 字段

**Validates: Requirements 3.1, 3.2, 3.4**

## Error Handling

| 错误场景 | 处理方式 |
|---------|---------|
| 证据段落超过上下文长度 | 跳过该问题，记录警告日志 |
| 小说长度不足以构建指定长度上下文 | 返回错误，终止测试 |
| 问题缺少 position 字段 | 跳过该问题，记录警告日志 |
| 无法获取足够的填充文本 | 使用可用的最大填充，记录警告 |
| 深度模式参数无效 | CLI 报错并显示帮助信息 |

## Testing Strategy

### 单元测试

1. **ContextBuilder 测试**
   - 测试不同深度值的上下文构建
   - 测试边界情况（深度 0% 和 100%）
   - 测试证据段落过长的处理
   - 测试填充文本的正确性

2. **DepthScheduler 测试**
   - 测试 uniform 模式的均匀分配
   - 测试 fixed 模式的固定深度
   - 测试多上下文长度的组合分配

3. **热力图测试**
   - 测试深度统计计算
   - 测试热力图生成

### Property-Based Tests

使用 Hypothesis 库进行属性测试：

1. **上下文长度属性测试** - 验证 Property 1
2. **深度位置属性测试** - 验证 Property 2
3. **均匀分配属性测试** - 验证 Property 4

### 集成测试

1. 端到端测试：从 CLI 到结果输出
2. 热力图生成测试：从结果文件到 HTML 输出
