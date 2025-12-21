# Requirements Document

## Introduction

本功能旨在改进长上下文模型的召回能力测试。当前测试方式只取小说前 N 个 token 作为上下文，导致所有被测试问题的答案都位于上下文前部，无法真正测试模型在不同深度位置的信息召回能力。

新功能将支持"深度感知测试"（Depth-Aware Testing），通过动态构建上下文，将答案放置在上下文的不同深度位置（0%、25%、50%、75%、100%），从而全面评估模型的长上下文召回能力，并生成二维热力图展示结果。

## Glossary

- **Depth（深度）**: 答案在上下文中的相对位置，0% 表示开头，100% 表示结尾
- **Evidence（证据段落）**: 包含问题答案的原始文本片段
- **Prefix（前缀填充）**: 放置在证据段落之前的填充文本
- **Suffix（后缀填充）**: 放置在证据段落之后的填充文本
- **Context_Builder（上下文构建器）**: 根据目标深度动态构建测试上下文的组件
- **Depth_Heatmap（深度热力图）**: 展示不同上下文长度和答案深度组合下准确率的二维热力图
- **Testing_Tool（测试工具）**: 执行 LLM 测试的核心组件

## Requirements

### Requirement 1: 上下文构建器

**User Story:** 作为测试人员，我希望能够为每个问题动态构建指定深度的上下文，以便测试模型在不同位置的召回能力。

#### Acceptance Criteria

1. WHEN 给定一个问题、目标深度和上下文长度 THEN Context_Builder SHALL 构建一个包含证据段落的上下文，其中证据段落位于指定深度位置
2. WHEN 目标深度为 0% THEN Context_Builder SHALL 将证据段落放置在上下文开头
3. WHEN 目标深度为 50% THEN Context_Builder SHALL 将证据段落放置在上下文中间位置
4. WHEN 目标深度为 100% THEN Context_Builder SHALL 将证据段落放置在上下文末尾
5. WHEN 构建上下文时 THEN Context_Builder SHALL 使用小说中不包含答案的其他部分作为填充文本
6. WHEN 证据段落长度超过可用空间 THEN Context_Builder SHALL 返回错误或跳过该问题
7. THE Context_Builder SHALL 确保最终上下文长度等于指定的 context_length（允许 ±1% 误差）

### Requirement 2: 深度感知测试模式

**User Story:** 作为测试人员，我希望能够在测试时指定深度策略，以便系统自动为每个问题分配测试深度。

#### Acceptance Criteria

1. WHEN 用户指定 `--depth-mode uniform` THEN Testing_Tool SHALL 将问题均匀分配到 5 个深度区间（0%、25%、50%、75%、100%）
2. WHEN 用户指定 `--depth-mode fixed --depth 50` THEN Testing_Tool SHALL 将所有问题的答案放置在 50% 深度位置
3. WHEN 用户不指定深度模式 THEN Testing_Tool SHALL 使用传统模式（取小说前 N 个 token）以保持向后兼容
4. WHEN 使用深度感知模式测试 THEN Testing_Tool SHALL 在结果中记录每个问题的实际测试深度
5. WHEN 问题无法在指定深度构建有效上下文 THEN Testing_Tool SHALL 跳过该问题并记录原因

### Requirement 3: 测试结果扩展

**User Story:** 作为测试人员，我希望测试结果包含深度信息，以便后续分析和可视化。

#### Acceptance Criteria

1. WHEN 使用深度感知模式测试 THEN Testing_Tool SHALL 在每个结果中添加 `depth` 字段记录测试深度（0.0-1.0）
2. WHEN 使用深度感知模式测试 THEN Testing_Tool SHALL 在每个结果中添加 `depth_bin` 字段记录深度区间标签（如 "0%", "25%", "50%", "75%", "100%"）
3. WHEN 保存结果时 THEN Testing_Tool SHALL 在 metadata 中记录使用的深度模式和参数
4. THE Testing_Tool SHALL 保持与现有结果格式的兼容性，新字段为可选字段

### Requirement 4: 二维深度热力图

**User Story:** 作为测试人员，我希望能够生成二维热力图，展示不同上下文长度和答案深度组合下的模型准确率。

#### Acceptance Criteria

1. WHEN 用户指定 `--mode depth` THEN Heatmap_Generator SHALL 生成二维热力图
2. THE Depth_Heatmap SHALL 以上下文长度为纵轴（如 32K、64K、128K、200K）
3. THE Depth_Heatmap SHALL 以答案深度为横轴（0%、25%、50%、75%、100%）
4. THE Depth_Heatmap SHALL 使用颜色深浅表示准确率（绿色=高，红色=低，灰色=无数据）
5. WHEN 鼠标悬停在热力图单元格上 THEN Depth_Heatmap SHALL 显示详细信息（准确率、问题数量、上下文长度、深度）
6. THE Depth_Heatmap SHALL 在标题中显示模型名称和数据集信息
7. WHEN 某个单元格没有测试数据 THEN Depth_Heatmap SHALL 显示为灰色并标注"无数据"

### Requirement 5: 多上下文长度测试支持

**User Story:** 作为测试人员，我希望能够在一次测试中指定多个上下文长度，以便生成完整的二维热力图数据。

#### Acceptance Criteria

1. WHEN 用户指定 `--context-lengths 32000,64000,128000,200000` THEN Testing_Tool SHALL 对每个上下文长度分别执行测试
2. WHEN 使用多上下文长度模式 THEN Testing_Tool SHALL 为每个 (context_length, depth) 组合分配适当数量的问题
3. WHEN 问题数量不足以覆盖所有组合 THEN Testing_Tool SHALL 优先保证每个组合至少有最小数量的问题（如 5 个）
4. THE Testing_Tool SHALL 在结果中记录每个问题使用的 context_length
5. WHEN 保存结果时 THEN Testing_Tool SHALL 将所有上下文长度的结果保存到同一个输出文件

### Requirement 6: CLI 参数扩展

**User Story:** 作为测试人员，我希望通过命令行参数控制深度感知测试的行为。

#### Acceptance Criteria

1. THE Testing_Tool CLI SHALL 支持 `--depth-mode` 参数，可选值为 `legacy`、`uniform`、`fixed`
2. THE Testing_Tool CLI SHALL 支持 `--depth` 参数，用于 fixed 模式指定固定深度（0-100）
3. THE Testing_Tool CLI SHALL 支持 `--context-lengths` 参数，接受逗号分隔的多个上下文长度值
4. WHEN 使用 `--context-lengths` 时 THEN `--context_length` 参数 SHALL 被忽略
5. THE Heatmap CLI SHALL 支持 `--mode depth` 选项生成深度热力图
6. IF 参数组合无效 THEN CLI SHALL 显示清晰的错误信息并退出
