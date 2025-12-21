# 实现计划：问题验证模块

## 概述

实现问题验证模块，通过 LLM 回溯验证和原文证据匹配来检测和过滤生成问题中的幻觉。

## 任务

- [x] 1. 创建验证提示词模板
  - 在 `prompts/validation.json` 创建验证提示词
  - 提示词要求 LLM 独立回答问题、提供原文证据、判断可回答性和置信度
  - 定义 JSON 输出格式
  - _需求: 7.1, 7.3, 2.1, 3.1, 3.3_

- [x] 2. 实现 EvidenceMatcher 证据匹配器
  - [x] 2.1 创建 `src/validator/evidence_matcher.py`
    - 实现文本标准化方法（去除多余空格、统一标点）
    - 实现子串匹配查找
    - 实现相似度计算（使用 difflib.SequenceMatcher）
    - _需求: 2.2, 2.3, 2.4, 2.5_
  - [ ]* 2.2 编写 EvidenceMatcher 属性测试
    - **Property 2: 证据存在性验证**
    - **验证: 需求 2.2, 2.3, 2.4, 2.5**

- [x] 3. 实现 ValidationResult 数据模型
  - [x] 3.1 创建 `src/validator/validation_result.py`
    - 定义 ValidationResult dataclass
    - 实现 to_dict() 序列化方法
    - 实现 from_dict() 反序列化方法
    - _需求: 4.1, 4.4_
  - [ ]* 3.2 编写 ValidationResult 属性测试
    - **Property 3: 验证结果完整性**
    - **Property 4: 失败原因追溯**
    - **验证: 需求 4.1**

- [x] 4. 实现答案比较逻辑
  - [x] 4.1 在 `src/validator/answer_comparator.py` 创建答案比较器
    - 实现单选题答案比较（完全匹配）
    - 实现多选题答案比较（集合相等）
    - _需求: 1.2, 1.3, 1.4, 1.5_
  - [ ]* 4.2 编写答案比较属性测试
    - **Property 1: 答案匹配一致性**
    - **验证: 需求 1.2, 1.3, 1.4, 1.5**

- [x] 5. 实现 QuestionValidator 核心类
  - [x] 5.1 创建 `src/validator/question_validator.py`
    - 实现 validate_question() 单问题验证
    - 解析 LLM 响应 JSON
    - 调用 EvidenceMatcher 验证证据
    - 调用答案比较器验证答案
    - 综合判断 is_valid
    - _需求: 1.1, 1.2, 2.2, 3.2, 3.4_
  - [ ]* 5.2 编写综合验证逻辑属性测试
    - **Property 5: 综合验证逻辑**
    - **验证: 需求 1.2, 2.2, 3.2, 3.4**

- [x] 6. 实现批量验证功能
  - [x] 6.1 在 QuestionValidator 中实现 validate_batch()
    - 支持并发验证
    - 实现重试机制
    - 从 novel_tokens 提取每个问题的上下文
    - _需求: 5.1, 5.2, 5.3_
  - [ ]* 6.2 编写统计一致性属性测试
    - **Property 6: 统计一致性**
    - **验证: 需求 4.2**

- [x] 7. 更新 PromptTemplateManager
  - 在 `src/core/prompt_template.py` 添加 get_validation_prompt() 方法
  - 支持加载 validation.json 模板
  - _需求: 7.2_

- [x] 8. 创建 validator 模块结构
  - 创建 `src/validator/__init__.py`
  - 导出 QuestionValidator, ValidationResult, EvidenceMatcher
  - _需求: 无（代码组织）_

- [x] 9. 实现 CLI 入口
  - [x] 9.1 创建 `src/validate.py` CLI 入口
    - 解析命令行参数（问题集路径、小说路径、输出路径、并发数、置信度阈值）
    - 加载配置和初始化组件
    - 调用 validate_batch()
    - 输出验证摘要统计
    - 支持 --valid-only 参数仅输出通过的问题
    - _需求: 6.1, 6.2, 6.3, 6.4_

- [x] 10. Checkpoint - 确保所有测试通过
  - 运行所有单元测试和属性测试
  - 如有问题请询问用户

- [ ] 11. 集成测试
  - [ ]* 11.1 编写端到端集成测试
    - 使用真实问题数据测试完整验证流程
    - 验证 JSONL 输出格式正确
    - _需求: 4.3_

- [x] 12. 更新测试工具以支持验证数据
  - [x] 12.1 创建 `src/tester/question_checker.py` 问题预检查模块
    - 实现 check_questions() 方法，遍历所有问题进行预检查
    - 检查 validation 字段是否存在
    - 检查 validation.is_valid 是否为 true
    - 收集所有问题后统一报告错误（问题索引、问题内容、失败原因）
    - _需求: 8.1, 8.2, 8.3, 8.8_
  - [x] 12.2 修改 `src/tester/testing_tool.py`
    - 在 run_tests() 开始时调用预检查模块
    - 根据参数决定检查行为
    - _需求: 8.1, 8.4, 8.5_
  - [x] 12.3 修改 `src/test.py` CLI
    - 添加 `--skip-validation` 参数，跳过验证字段检查
    - 添加 `--ignore-invalid` 参数，自动过滤无效问题
    - 输出跳过的问题数量和位置日志
    - _需求: 8.4, 8.5, 8.6, 8.7_

- [ ] 13. 更新文档
  - 在 README 中添加验证功能说明
  - 添加 CLI 使用示例
  - 说明测试工具的新参数
  - _需求: 无（文档）_

## 备注

- 标记 `*` 的任务为可选测试任务，可跳过以加快 MVP 开发
- 每个任务引用具体需求以便追溯
- 属性测试验证核心正确性属性
