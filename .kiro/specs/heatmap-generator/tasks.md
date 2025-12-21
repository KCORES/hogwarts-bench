# Implementation Plan: Heatmap Generator

## Overview

实现热力图生成器模块，用于可视化问题覆盖度和模型正确度。采用增量开发方式，先实现核心数据处理，再实现可视化，最后添加 CLI 接口。

## Tasks

- [x] 1. 创建数据模型和加载器
  - [x] 1.1 创建 `src/reporter/heatmap.py` 文件，定义数据类 `QuestionPosition`, `QuestionEntry`, `ResultEntry`, `BinStats`
    - 使用 dataclass 定义数据结构
    - _Requirements: 1.1, 2.1_
  - [x] 1.2 实现 `load_question_data` 函数
    - 从 JSONL 加载问题数据
    - 跳过 metadata 行
    - 验证必需字段 (position.start_pos, position.end_pos)
    - 返回 (valid_entries, skipped_count)
    - _Requirements: 1.1, 5.1, 5.3, 5.4_
  - [x] 1.3 实现 `load_result_data` 函数
    - 从 JSONL 加载结果数据
    - 跳过 metadata 行
    - 验证必需字段 (position, score)
    - 返回 (valid_entries, skipped_count)
    - _Requirements: 2.1, 5.2, 5.3, 5.4_
  - [ ]* 1.4 编写数据加载属性测试
    - **Property 1: Data Parsing Round-Trip**
    - **Property 10: Data Validation Correctness**
    - **Property 11: Invalid Data Skipping**
    - **Property 12: Entry Count Conservation**
    - **Validates: Requirements 1.1, 2.1, 5.1, 5.2, 5.3, 5.4**

- [x] 2. 实现 Bin 计算逻辑
  - [x] 2.1 实现 `calculate_coverage_bins` 函数
    - 将上下文划分为 num_bins 个区间
    - 计算每个问题在各 bin 的比例覆盖
    - 归一化覆盖度到 [0, 1]
    - _Requirements: 1.2, 1.3, 1.4_
  - [x] 2.2 实现 `calculate_accuracy_bins` 函数
    - 将上下文划分为 num_bins 个区间
    - 计算每个 bin 的平均得分
    - 空 bin 的 accuracy 设为 None
    - _Requirements: 2.2, 2.3_
  - [ ]* 2.3 编写 Bin 计算属性测试
    - **Property 2: Bin Count Matches Configuration**
    - **Property 3: Proportional Coverage Conservation**
    - **Property 4: Coverage Values Bounded**
    - **Property 5: Accuracy Equals Average Score**
    - **Property 6: Empty Bins Have None Accuracy**
    - **Validates: Requirements 1.2, 1.3, 1.4, 2.2, 2.3**

- [x] 3. Checkpoint - 确保核心逻辑测试通过
  - 运行所有测试，确保数据加载和 bin 计算正确
  - 如有问题，询问用户

- [x] 4. 实现热力图生成
  - [x] 4.1 实现 `create_coverage_heatmap` 函数
    - 使用 Plotly 创建水平热力图
    - 使用蓝色渐变色表示覆盖密度
    - 添加悬停信息显示 bin 详情
    - _Requirements: 1.5_
  - [x] 4.2 实现 `create_accuracy_heatmap` 函数
    - 使用 Plotly 创建水平热力图
    - 使用红-黄-绿渐变色表示正确率
    - 空 bin 显示为灰色
    - _Requirements: 2.4, 2.5_
  - [x] 4.3 实现 `create_combined_heatmap` 函数
    - 创建两行对齐的热力图
    - 上行显示覆盖度，下行显示正确度
    - 共享 x 轴显示 token 位置
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]* 4.4 编写组合热力图属性测试
    - **Property 7: Combined Heatmap Bin Consistency**
    - **Validates: Requirements 3.3**

- [x] 5. 实现 CLI 接口
  - [x] 5.1 创建 `src/heatmap.py` CLI 入口文件
    - 使用 argparse 定义参数
    - --mode: coverage/accuracy/combined
    - --questions: 问题数据文件路径
    - --results: 结果数据文件路径
    - --output: 输出 HTML 文件路径
    - --bins: bin 数量 (默认 50)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x] 5.2 实现参数验证逻辑
    - coverage 模式需要 --questions
    - accuracy 模式需要 --results
    - combined 模式需要 --questions 和 --results
    - _Requirements: 4.6, 4.7, 4.8_
  - [ ]* 5.3 编写 CLI 属性测试
    - **Property 8: Mode Parameter Validation**
    - **Property 9: Bins Parameter Configuration**
    - **Validates: Requirements 4.1, 4.5**

- [x] 6. Final Checkpoint - 确保所有测试通过
  - 运行完整测试套件
  - 如有问题，询问用户

## Notes

- 标记 `*` 的任务为可选测试任务，可跳过以加快 MVP 开发
- 每个任务引用具体需求以确保可追溯性
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况
