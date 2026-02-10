---

### 文件 2: `user.md`

该文档详细描述了从 0 到 1 的搭建流程、页面功能拆解以及具体的技术实现细节，作为开发手册使用。

```markdown
# 🛠️ 项目开发指南：从 0 到 1 搭建工作流

本文档详细拆解 **Personal Scholar Agent** 的全栈开发流程，涵盖前端页面逻辑、后端 Agent 工作流设计及核心技术实现。

---

## 一、 前端开发架构 (Vue 3)

前端主要包含三个核心页面，通过 Router 进行管理。

### 1. 首页 / 论文上传页 (Home & Upload)
* **功能描述**: 
    * 提供文件拖拽上传区域。
    * 提供配置选项：目标翻译语言（默认为中文）、选择摘要模版（默认 `tinghua.md`）。
    * 展示最近上传任务的进度条。
* **技术实现**:
    * 使用 `el-upload` 组件处理文件流。
    * **Axios**: 将 PDF 文件以 `FormData` 形式发送给后端 `/api/upload` 接口。
    * **WebSocket/SSE**: 建立长连接，实时监听后端 Agent 的处理状态（如：`Parsing` -> `Translating` -> `Summarizing` -> `Done`）。

### 2. 论文仪表盘 (Dashboard)
* **功能描述**:
    * 以卡片或列表形式展示所有已处理的论文。
    * 支持按“领域”（如 Backdoor Attacks, Time Series）标签过滤。
    * 显示论文元数据（标题、作者、发表年份）。
* **技术实现**:
    * **状态管理 (Pinia)**: 缓存论文列表数据，减少重复请求。
    * **搜索与过滤**: 前端基于计算属性实现快速筛选。

### 3. 沉浸式阅读页 (Reading Workspace)
* **功能描述**:
    * **左右分屏布局**: 左侧显示 PDF 原文，右侧显示 Agent 生成的内容（翻译/摘要/改进建议）。
    * **Tab 切换**: 右侧面板包含 "Full Translation", "Core Ideas (Tinghua)", "Improvements" 三个标签页。
    * **Chat 悬浮窗**: 针对当前论文的 RAG 问答助手。
* **技术实现**:
    * **PDF.js**: 渲染 PDF，并支持高亮选中文字。
    * **Markdown Renderer**: 渲染后端生成的 Markdown 内容，支持 LaTeX 公式显示。

---

## 二、 后端 Agent 工作流 (Python + LangGraph)

后端采用 **LangGraph** 构建有向无环图 (DAG) 工作流，确保步骤的可控性与容错性。

### 阶段 1：环境与基础设施搭建
* **向量数据库部署**: 使用 Docker 部署 Milvus 或 ChromaDB。用于存储论文的文本块 (Chunks) embedding，支撑 RAG 检索。
* **文件系统规划**: 
    * `data/raw/`: 存放原始 PDF。
    * `data/processed/{paper_id}/`: 存放生成的 `translation.md`, `summary.md`, `improvement.md`。

### 阶段 2：核心功能开发 (Agent Skills)

#### Step 1: 文档解析 (Parser Node)
* **任务**: 将 PDF 转换为机器可读文本，同时提取图片/表格。
* **技术**: 
    * 使用 `PyMuPDF` 或 `Unstructured` 提取文本。
    * **OCR 增强**: 针对老旧扫描版论文，集成 `PaddleOCR` 提取文字。

#### Step 2: 翻译 Agent (Translation Node)
* **任务**: 按段落/页面进行对照翻译。
* **技术**: 
    * **Prompt Engineering**: 设计 System Prompt，要求保留 LaTeX 公式（如 $x$）不被翻译。
    * **流式输出**: 利用 LLM 的 Stream 特性，将翻译结果实时写入 Markdown 文件。

#### Step 3: 核心思路提取 Agent (Summary Node)
* **任务**: 读取 `tinghua.md` 并在生成时严格遵循其结构。
* **技术**: 
    * **In-Context Learning**: 将 `tinghua.md` 的内容作为 Few-Shot 样本注入 Prompt。
    * **Map-Reduce 链**: 如果论文过长（如 > 20页），先分块总结（Map），再通过 Prompt 汇总（Reduce）到模版结构中。
    * **Output Parser**: 强制模型输出 JSON 或标准 Markdown 格式，确保结构一致。

#### Step 4: 改进方案生成 Agent (Critique Node)
* **任务**: 分析论文的 Future Work 和 Limitation，提出改进点。
* **技术**: 
    * **CoT (Chain of Thought)**: 引导模型思考 -> "这篇论文的方法缺限在哪里？" -> "结合后门攻击领域的最新进展（检索向量库），有什么新技术可以弥补？" -> "生成改进方案"。
    * **RAG**: 检索库中已有的“后门攻击”相关论文，对比寻找差异化创新点。

### 阶段 3：知识库构建 (RAG Pipeline)
* **入库**: 在 Step 1 解析完成后，使用 `LangChain` 的 `RecursiveCharacterTextSplitter` 对文本切片，调用 Embedding 模型（如 OpenAI 或 HuggingFace 本地模型）存入向量数据库。
* **检索**: 当用户在前端提问时，将问题向量化，匹配最相关的 Top-K 片段，辅助 LLM 回答。

---

## 三、 进阶优化 (Optimization)

### 1. 模型微调 (Fine-tuning)
* **场景**: 通用大模型对“后门攻击”领域的专有名词（如 "Clean-label attacks", "Trigger transparency"）理解不深。
* **方案**: 
    * 收集您历史积攒的领域论文。
    * 使用 **QLoRA** 技术，在消费级显卡上对 LLaMA 3 或 Qwen 进行参数高效微调 (PEFT)。
    * 增强模型对领域术语的敏感度和翻译准确度。

### 2. 提示词调优 (Prompt Tuning)
* **策略**: 使用 **ToT (Tree of Thoughts)** 策略，让 Agent 在生成“改进方案”时，先生成 3 个不同的方向，然后自我评估哪个方向最具可行性，最后输出最佳方案。

### 3. 输出标准化
* 最终输出为物理文件夹 `OUTPUT/{Paper_Title}/`，结构如下：
    ```text
    ├── original.pdf
    ├── translated_full.md      # 全文翻译
    ├── summary_tinghua.md      # 核心思路 (基于模版)
    ├── improvements.md         # 改进方案建议
    └── assets/                 # 提取出的图片与公式
    ```