# Requirements Document

## Introduction

本功能为 Hogwarts Bench 测试框架添加热力图生成器，用于可视化测试问题在上下文中的分布覆盖情况，以及大模型测试结果在不同上下文区域的正确程度。支持三种展示模式：单独的问题覆盖度热力图、单独的正确度热力图，以及两者合并对齐展示的组合热力图。

## Glossary

- **Heatmap_Generator**: 热力图生成器模块，负责创建上下文覆盖和正确度可视化
- **Context_Region**: 上下文区域，将整个上下文按 token 位置划分为多个区间（bin）
- **Coverage_Heatmap**: 覆盖度热力图，展示问题在各上下文区域的分布密度
- **Accuracy_Heatmap**: 正确度热力图，展示各上下文区域的模型回答正确率
- **Combined_Heatmap**: 组合热力图，将覆盖度和正确度对齐展示在同一图表中
- **Question_Data**: 问题数据，包含问题位置信息的 JSONL 格式数据
- **Result_Data**: 测试结果数据，包含模型回答和评分的 JSONL 格式数据
- **Bin**: 区间，将上下文按固定大小划分的单元

## Requirements

### Requirement 1: 问题覆盖度热力图生成

**User Story:** As a researcher, I want to generate a coverage heatmap showing question distribution across context regions, so that I can understand how well my questions cover different parts of the context.

#### Acceptance Criteria

1. WHEN Question_Data is provided, THE Heatmap_Generator SHALL parse position information (start_pos, end_pos) from each question
2. WHEN generating Coverage_Heatmap, THE Heatmap_Generator SHALL divide the context into configurable number of bins (default: 50)
3. WHEN a question spans multiple bins, THE Heatmap_Generator SHALL count coverage proportionally in each overlapping bin
4. THE Heatmap_Generator SHALL normalize coverage values to a 0-1 scale for consistent visualization
5. WHEN Coverage_Heatmap is generated, THE Heatmap_Generator SHALL output an interactive HTML file using Plotly

### Requirement 2: 正确度热力图生成

**User Story:** As a researcher, I want to generate an accuracy heatmap showing model performance across context regions, so that I can identify which parts of the context the model handles well or poorly.

#### Acceptance Criteria

1. WHEN Result_Data is provided, THE Heatmap_Generator SHALL extract position and score information from each result
2. WHEN generating Accuracy_Heatmap, THE Heatmap_Generator SHALL calculate average score for each bin
3. WHEN a bin contains no questions, THE Heatmap_Generator SHALL mark it as having no data (distinct from zero accuracy)
4. THE Heatmap_Generator SHALL use a color gradient from red (low accuracy) to green (high accuracy)
5. WHEN Accuracy_Heatmap is generated, THE Heatmap_Generator SHALL output an interactive HTML file using Plotly

### Requirement 3: 组合热力图生成

**User Story:** As a researcher, I want to generate a combined heatmap showing both coverage and accuracy aligned together, so that I can correlate question distribution with model performance.

#### Acceptance Criteria

1. WHEN both Question_Data and Result_Data are provided, THE Heatmap_Generator SHALL generate Combined_Heatmap
2. THE Combined_Heatmap SHALL display coverage and accuracy as two aligned horizontal bars
3. THE Combined_Heatmap SHALL use consistent bin boundaries for both coverage and accuracy
4. THE Combined_Heatmap SHALL include a shared x-axis showing token positions
5. WHEN Combined_Heatmap is generated, THE Heatmap_Generator SHALL output an interactive HTML file using Plotly

### Requirement 4: 命令行接口

**User Story:** As a user, I want to generate heatmaps via command line, so that I can easily integrate this into my workflow.

#### Acceptance Criteria

1. THE Heatmap_Generator SHALL accept a `--mode` parameter with values: "coverage", "accuracy", or "combined"
2. THE Heatmap_Generator SHALL accept a `--questions` parameter for Question_Data file path
3. THE Heatmap_Generator SHALL accept a `--results` parameter for Result_Data file path
4. THE Heatmap_Generator SHALL accept an `--output` parameter for output HTML file path
5. THE Heatmap_Generator SHALL accept a `--bins` parameter for configuring number of bins (default: 50)
6. IF mode is "coverage" and `--questions` is not provided, THEN THE Heatmap_Generator SHALL return an error message
7. IF mode is "accuracy" and `--results` is not provided, THEN THE Heatmap_Generator SHALL return an error message
8. IF mode is "combined" and either `--questions` or `--results` is not provided, THEN THE Heatmap_Generator SHALL return an error message

### Requirement 5: 数据验证

**User Story:** As a user, I want the system to validate input data, so that I can be confident the heatmap accurately represents my data.

#### Acceptance Criteria

1. WHEN Question_Data is loaded, THE Heatmap_Generator SHALL validate that each question has position.start_pos and position.end_pos fields
2. WHEN Result_Data is loaded, THE Heatmap_Generator SHALL validate that each result has position and score fields
3. IF invalid data is encountered, THEN THE Heatmap_Generator SHALL skip the invalid entry and log a warning
4. WHEN data loading completes, THE Heatmap_Generator SHALL report the count of valid and skipped entries
