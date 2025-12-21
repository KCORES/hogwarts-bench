# 需求文档：问题验证模块

## 简介

问题验证模块用于检测和过滤 LLM 生成问题时产生的幻觉。通过 LLM 回溯验证和原文证据匹配，确保生成的问题准确、可回答，且答案有原文依据支撑。

## 术语表

- **Question_Validator**: 问题验证器，负责验证生成问题的质量
- **Verification_LLM**: 用于验证的大语言模型，独立于生成模型进行答案验证
- **Evidence**: 原文证据，支持答案的原文精确引用
- **Validation_Result**: 验证结果，包含验证状态和详细信息
- **Context**: 生成问题时使用的原文上下文片段

## 需求

### 需求 1：LLM 回溯验证

**用户故事：** 作为问题生成系统，我希望通过 LLM 独立回答问题来验证答案正确性，以便过滤掉答案标注错误的问题。

#### 验收标准

1. WHEN 验证一个问题时，THE Question_Validator SHALL 将问题和原始上下文发送给 Verification_LLM，但不包含标注答案
2. WHEN Verification_LLM 返回答案时，THE Question_Validator SHALL 比较模型答案与标注答案是否一致
3. IF 模型答案与标注答案不一致，THEN THE Question_Validator SHALL 将该问题标记为验证失败
4. WHEN 验证单选题时，THE Question_Validator SHALL 要求答案完全匹配
5. WHEN 验证多选题时，THE Question_Validator SHALL 要求答案集合完全匹配

### 需求 2：原文证据验证

**用户故事：** 作为问题生成系统，我希望验证答案是否有原文依据，以便过滤掉基于幻觉生成的问题。

#### 验收标准

1. WHEN 验证问题时，THE Question_Validator SHALL 要求 Verification_LLM 提供支持答案的原文引用
2. WHEN 收到原文引用时，THE Question_Validator SHALL 检查引用是否存在于原始上下文中
3. IF 原文引用在上下文中不存在，THEN THE Question_Validator SHALL 将该问题标记为证据验证失败
4. THE Question_Validator SHALL 使用模糊匹配来处理引用中的轻微差异（如空格、标点）
5. WHEN 引用匹配成功时，THE Question_Validator SHALL 记录匹配的相似度分数

### 需求 3：可回答性判断

**用户故事：** 作为问题生成系统，我希望判断问题是否可以仅从上下文回答，以便过滤掉需要外部知识的问题。

#### 验收标准

1. WHEN 验证问题时，THE Question_Validator SHALL 要求 Verification_LLM 判断问题是否可从上下文回答
2. IF Verification_LLM 判断问题不可回答，THEN THE Question_Validator SHALL 将该问题标记为不可回答
3. WHEN Verification_LLM 判断问题可回答时，THE Question_Validator SHALL 要求提供置信度评级（high/medium/low）
4. WHERE 配置了置信度阈值，THE Question_Validator SHALL 过滤低于阈值的问题

### 需求 4：验证结果输出

**用户故事：** 作为用户，我希望获得详细的验证结果，以便了解问题被接受或拒绝的原因。

#### 验收标准

1. THE Question_Validator SHALL 为每个问题生成包含以下字段的验证结果：验证状态、模型答案、原文证据、可回答性、置信度、失败原因
2. WHEN 验证完成时，THE Question_Validator SHALL 输出验证通过和失败的问题数量统计
3. THE Question_Validator SHALL 支持将验证结果保存为 JSONL 格式
4. WHEN 保存结果时，THE Question_Validator SHALL 在原问题数据中添加验证元数据

### 需求 5：批量验证与并发

**用户故事：** 作为用户，我希望能够高效地批量验证大量问题，以便节省时间和成本。

#### 验收标准

1. THE Question_Validator SHALL 支持并发验证多个问题
2. WHERE 配置了并发数，THE Question_Validator SHALL 限制同时进行的验证请求数量
3. WHEN 验证失败时，THE Question_Validator SHALL 支持重试机制
4. THE Question_Validator SHALL 显示验证进度信息

### 需求 6：CLI 集成

**用户故事：** 作为用户，我希望通过命令行工具验证问题集，以便方便地集成到工作流程中。

#### 验收标准

1. THE System SHALL 提供 `python -m src.validate` 命令行入口
2. THE CLI SHALL 接受以下参数：问题集路径、小说路径、输出路径、并发数、置信度阈值
3. WHEN 验证完成时，THE CLI SHALL 输出验证摘要统计信息
4. THE CLI SHALL 支持仅输出验证通过的问题到新文件

### 需求 7：验证提示词模板

**用户故事：** 作为开发者，我希望验证提示词可配置，以便根据需要调整验证策略。

#### 验收标准

1. THE System SHALL 在 prompts 目录下提供默认的验证提示词模板
2. THE Question_Validator SHALL 支持从外部文件加载自定义提示词
3. THE 提示词模板 SHALL 包含占位符用于插入上下文、问题和选项

### 需求 8：测试工具与验证数据集成

**用户故事：** 作为用户，我希望测试工具能够识别验证状态，以便只使用经过验证的高质量问题进行测试，并在测试前发现问题以节省 API 调用成本。

#### 验收标准

1. WHEN 加载问题集时，THE Testing_Tool SHALL 先遍历所有问题进行预检查，再开始测试
2. IF 问题集中存在缺少 validation 字段的问题，THEN THE Testing_Tool SHALL 立即停止并报错，列出缺少验证的问题位置
3. IF 问题集中存在 `validation.is_valid=false` 的问题，THEN THE Testing_Tool SHALL 立即停止并报错，列出无效问题的位置和失败原因
4. WHERE 用户指定 `--skip-validation` 参数，THE Testing_Tool SHALL 跳过验证字段检查，允许使用未验证的问题
5. WHERE 用户指定 `--ignore-invalid` 参数，THE Testing_Tool SHALL 自动跳过 `validation.is_valid=false` 的问题，仅使用有效问题进行测试
6. WHEN 使用 `--ignore-invalid` 参数时，THE Testing_Tool SHALL 在日志中输出跳过的问题数量和位置
7. IF 预检查或过滤后没有可用的问题，THEN THE Testing_Tool SHALL 停止执行并报错
8. THE Testing_Tool SHALL 在预检查阶段不进行任何 LLM API 调用，以节省成本
