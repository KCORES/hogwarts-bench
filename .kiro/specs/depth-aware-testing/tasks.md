# Implementation Plan: Depth-Aware Testing

## Overview

本实现计划将深度感知测试功能分解为可执行的编码任务。按照依赖关系排序，先实现核心组件，再扩展现有模块，最后添加 CLI 支持和可视化。

**热力图坐标轴说明：**
- 横轴（X轴）：上下文长度（如 32K、64K、128K、200K）
- 纵轴（Y轴）：答案深度（0%、25%、50%、75%、100%）

## Tasks

- [x] 1. 实现 ContextBuilder 上下文构建器
  - [x] 1.1 创建 `src/tester/context_builder.py` 文件，定义 ContextBuildResult 数据类和 ContextBuilder 类框架
    - 定义 ContextBuildResult dataclass
    - 定义 ContextBuilder 类的 __init__ 方法
    - _Requirements: 1.1, 1.7_

  - [x] 1.2 实现 `_extract_evidence` 方法，提取证据段落
    - 根据 position 信息提取证据 token
    - 添加前后 padding 确保完整性
    - _Requirements: 1.5_

  - [x] 1.3 实现 `_get_filler_tokens` 方法，获取填充文本
    - 从小说中选取不包含证据的连续文本
    - 支持指定长度的填充获取
    - _Requirements: 1.5_

  - [x] 1.4 实现 `build_context` 核心方法
    - 根据目标深度计算前缀和后缀长度
    - 组装 prefix + evidence + suffix
    - 处理边界情况（深度 0% 和 100%）
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7_

  - [ ]* 1.5 编写 ContextBuilder 单元测试
    - 测试不同深度值的构建
    - 测试边界情况
    - 测试错误处理
    - _Requirements: 1.1-1.7_

- [x] 2. 实现 DepthScheduler 深度调度器
  - [x] 2.1 创建 `src/tester/depth_scheduler.py` 文件，定义枚举和数据类
    - 定义 DepthMode 枚举
    - 定义 DepthAssignment dataclass
    - 定义 DepthScheduler 类框架
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 实现 `_schedule_uniform` 均匀分配策略
    - 将问题均匀分配到 5 个深度区间
    - 支持多上下文长度的组合分配
    - _Requirements: 2.1, 5.2_

  - [x] 2.3 实现 `_schedule_fixed` 固定深度策略
    - 所有问题使用相同的固定深度
    - _Requirements: 2.2_

  - [x] 2.4 实现 `schedule` 主方法
    - 根据模式调用对应的分配策略
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 2.5 编写 DepthScheduler 单元测试
    - 测试均匀分配的平衡性
    - 测试固定深度分配
    - _Requirements: 2.1, 2.2_

- [x] 3. Checkpoint - 核心组件完成
  - 确保 ContextBuilder 和 DepthScheduler 测试通过
  - 如有问题请询问用户

- [x] 4. 扩展 TestingTool 支持深度感知测试
  - [x] 4.1 在 `testing_tool.py` 中添加 `run_depth_aware_tests` 方法框架
    - 定义方法签名和参数
    - 添加日志输出
    - _Requirements: 2.3, 2.4, 2.5_

  - [x] 4.2 集成 ContextBuilder 和 DepthScheduler
    - 初始化组件
    - 为每个问题构建上下文并执行测试
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 4.3 扩展结果格式，添加深度相关字段
    - 在结果中添加 depth、depth_bin、test_context_length 字段
    - 更新 metadata 格式
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 4.4 编写 TestingTool 深度感知测试的集成测试
    - 测试端到端流程
    - _Requirements: 2.1-2.5, 3.1-3.4_

- [x] 5. 扩展 CLI 支持深度感知参数
  - [x] 5.1 在 `src/test.py` 中添加新的命令行参数
    - 添加 --depth-mode 参数
    - 添加 --depth 参数
    - 添加 --context-lengths 参数
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 5.2 实现参数验证和模式切换逻辑
    - 验证参数组合有效性
    - 根据参数选择调用 run_tests 或 run_depth_aware_tests
    - _Requirements: 6.4, 6.6_

- [x] 6. Checkpoint - 测试功能完成
  - 确保深度感知测试可以通过 CLI 执行
  - 如有问题请询问用户

- [x] 7. 实现深度热力图可视化
  - [x] 7.1 在 `src/reporter/heatmap.py` 中添加 DepthBinStats 数据类和 calculate_depth_bins 函数
    - 定义数据结构
    - 实现统计计算逻辑
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 7.2 实现 `create_depth_heatmap` 函数
    - 创建二维热力图
    - 横轴（X轴）：上下文长度（32K、64K、128K、200K 等）
    - 纵轴（Y轴）：答案深度（0%、25%、50%、75%、100%）
    - 配置颜色映射（绿色=高准确率，红色=低准确率，灰色=无数据）
    - 配置悬停信息（准确率、问题数量、上下文长度、深度）
    - 添加标题和品牌信息
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ]* 7.3 编写热力图单元测试
    - 测试统计计算
    - 测试 HTML 生成
    - _Requirements: 4.1-4.7_

- [x] 8. 扩展热力图 CLI
  - [x] 8.1 在 `src/heatmap.py` 中添加 depth 模式支持
    - 添加 --mode depth 选项
    - 实现深度热力图生成流程
    - _Requirements: 6.5_

- [x] 9. 更新使用文档
  - [x] 9.1 更新 README.md 添加深度感知测试使用说明
    - 添加深度感知测试的命令示例
    - 说明 --depth-mode、--depth、--context-lengths 参数用法
    - 添加深度热力图生成示例
    - _Requirements: 6.1-6.5_

  - [x] 9.2 更新 README_zh_CN.md 中文文档
    - 同步英文文档的更新内容
    - _Requirements: 6.1-6.5_

- [x] 10. Final Checkpoint - 功能完成
  - 确保所有测试通过
  - 验证端到端流程
  - 如有问题请询问用户

## Notes

- 任务按依赖关系排序，1-2 为核心组件，4-5 为测试扩展，7-8 为可视化
- 标记 `*` 的子任务为可选测试任务
- 每个 Checkpoint 用于验证阶段性成果
- Property-based tests 可在后续迭代中添加
