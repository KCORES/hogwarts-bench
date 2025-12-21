# 设计文档：问题验证模块

## 概述

问题验证模块通过 LLM 回溯验证和原文证据匹配来检测和过滤生成问题中的幻觉。验证流程包括：让验证模型独立回答问题、提取原文证据、判断可回答性，最终综合判断问题是否通过验证。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (validate.py)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   QuestionValidator                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ LLM Client  │  │  Evidence   │  │  Validation Result  │  │
│  │             │  │  Matcher    │  │     Builder         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PromptTemplateManager                      │
│              (validation_prompt.json)                        │
└─────────────────────────────────────────────────────────────┘
```

## 组件与接口

### QuestionValidator 类

```python
class QuestionValidator:
    """问题验证器核心类"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        prompt_manager: PromptTemplateManager,
        similarity_threshold: float = 0.8,
        confidence_threshold: str = "medium"
    ):
        """
        初始化验证器
        
        Args:
            llm_client: LLM 客户端
            prompt_manager: 提示词管理器
            similarity_threshold: 证据匹配相似度阈值
            confidence_threshold: 置信度阈值 (high/medium/low)
        """
        pass
    
    async def validate_question(
        self,
        question: Dict,
        context: str
    ) -> ValidationResult:
        """
        验证单个问题
        
        Args:
            question: 问题字典，包含 question, choice, answer 等字段
            context: 原始上下文文本
            
        Returns:
            ValidationResult 对象
        """
        pass
    
    async def validate_batch(
        self,
        questions: List[Dict],
        novel_tokens: List[int],
        concurrency: int = 5
    ) -> List[ValidationResult]:
        """
        批量验证问题
        
        Args:
            questions: 问题列表
            novel_tokens: 小说 token 列表（用于提取上下文）
            concurrency: 并发数
            
        Returns:
            验证结果列表
        """
        pass
```

### ValidationResult 数据模型

```python
@dataclass
class ValidationResult:
    """验证结果数据类"""
    
    # 原始问题数据
    question: Dict
    
    # 验证状态
    is_valid: bool
    
    # 详细验证信息
    model_answer: List[str]          # 验证模型的答案
    answer_matches: bool              # 答案是否匹配
    evidence: str                     # 原文证据引用
    evidence_found: bool              # 证据是否在原文中找到
    evidence_similarity: float        # 证据匹配相似度
    is_answerable: bool               # 是否可从上下文回答
    confidence: str                   # 置信度 (high/medium/low)
    
    # 失败原因（如果验证失败）
    failure_reasons: List[str]
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        pass
```

### EvidenceMatcher 类

```python
class EvidenceMatcher:
    """原文证据匹配器"""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化匹配器
        
        Args:
            similarity_threshold: 相似度阈值
        """
        pass
    
    def find_evidence(
        self,
        evidence: str,
        context: str
    ) -> Tuple[bool, float, Optional[str]]:
        """
        在上下文中查找证据
        
        Args:
            evidence: 待查找的证据文本
            context: 原始上下文
            
        Returns:
            (是否找到, 相似度分数, 匹配的原文片段)
        """
        pass
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本（去除多余空格、标点等）"""
        pass
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度"""
        pass
```

## 数据模型

### 验证请求格式

```json
{
  "question": "在德思礼一家为躲避信件而连夜出逃的过程中...",
  "question_type": "single_choice",
  "choice": {
    "a": "铁路风景旅馆十七号房间",
    "b": "破釜酒吧的阁楼",
    "c": "礁石上的小屋",
    "d": "女贞路四号碗柜"
  },
  "answer": ["a"],
  "position": {
    "start_pos": 25632,
    "end_pos": 55632
  }
}
```

### 验证响应格式（LLM 输出）

```json
{
  "answer": ["a"],
  "evidence": "他们在一家阴暗破旧的旅馆过了一夜...",
  "is_answerable": true,
  "confidence": "high",
  "reasoning": "原文明确提到他们在旅馆过夜..."
}
```

### 验证结果输出格式

```json
{
  "question": "在德思礼一家为躲避信件而连夜出逃的过程中...",
  "question_type": "single_choice",
  "choice": {...},
  "answer": ["a"],
  "position": {...},
  "validation": {
    "is_valid": true,
    "model_answer": ["a"],
    "answer_matches": true,
    "evidence": "他们在一家阴暗破旧的旅馆过了一夜...",
    "evidence_found": true,
    "evidence_similarity": 0.95,
    "is_answerable": true,
    "confidence": "high",
    "failure_reasons": []
  }
}
```

## 正确性属性

*正确性属性是系统应该在所有有效执行中保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。*

### Property 1: 答案匹配一致性
*对于任意*标注答案和模型答案：
- 单选题：当且仅当两个答案列表完全相等时，`answer_matches` 为 `true`
- 多选题：当且仅当两个答案集合完全相等时（忽略顺序），`answer_matches` 为 `true`

**验证: 需求 1.2, 1.3, 1.4, 1.5**

### Property 2: 证据存在性验证
*对于任意*证据文本和上下文：
- 如果证据的标准化形式（去除多余空格、统一标点）作为子串存在于上下文的标准化形式中，则 `evidence_found` 为 `true`
- 如果证据不存在于上下文中，则 `evidence_found` 为 `false`
- 相似度分数必须在 [0.0, 1.0] 范围内

**验证: 需求 2.2, 2.3, 2.4, 2.5**

### Property 3: 验证结果完整性
*对于任意*验证结果，必须包含所有必需字段：
- `is_valid`: bool
- `model_answer`: List[str]
- `answer_matches`: bool
- `evidence`: str
- `evidence_found`: bool
- `evidence_similarity`: float
- `is_answerable`: bool
- `confidence`: str (high/medium/low)
- `failure_reasons`: List[str]

**验证: 需求 4.1**

### Property 4: 失败原因追溯
*对于任意*验证结果：
- 如果 `is_valid=false`，则 `failure_reasons` 必须非空
- 如果 `is_valid=true`，则 `failure_reasons` 必须为空列表
- `failure_reasons` 中的每个原因必须对应一个具体的验证失败条件

**验证: 需求 4.1**

### Property 5: 综合验证逻辑
*对于任意*验证结果和置信度阈值配置：
```
is_valid = answer_matches AND evidence_found AND is_answerable AND (confidence >= threshold)
```
其中置信度比较规则：high > medium > low

**验证: 需求 1.2, 2.2, 3.2, 3.4**

### Property 6: 统计一致性
*对于任意*批量验证结果：
- `passed_count + failed_count = total_count`
- `passed_count` 等于 `is_valid=true` 的结果数量
- `failed_count` 等于 `is_valid=false` 的结果数量

**验证: 需求 4.2**

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| LLM 返回格式错误 | 重试最多 3 次，仍失败则标记为验证失败 |
| LLM 超时 | 重试最多 3 次，仍失败则标记为验证失败 |
| 证据为空 | 标记为证据验证失败 |
| 上下文提取失败 | 跳过该问题，记录错误日志 |

## 测试策略

### 单元测试
- EvidenceMatcher 的文本匹配逻辑
- ValidationResult 的序列化/反序列化
- 答案比较逻辑（单选/多选）

### 属性测试
- Property 1: 生成随机答案对，验证匹配逻辑一致性
- Property 2: 生成随机文本和子串，验证证据查找正确性
- Property 5: 生成随机验证结果组合，验证综合判断逻辑

### 集成测试
- 端到端验证流程测试
- CLI 命令测试
