<template>
  <main class="workspace-page">
    <section class="left-pane">
      <div class="pane-head">
        <h2>{{ paper?.title || "阅读工作台" }}</h2>
        <el-tag type="info">原文 PDF</el-tag>
      </div>
      <iframe v-if="paper" :src="pdfUrl" class="pdf-frame" title="论文 PDF 查看器" />
      <el-empty v-else description="未找到该论文" />
    </section>

    <section class="right-pane">
      <div class="pane-head">
        <div class="head-left">
          <el-button @click="$router.push('/dashboard')">返回总览</el-button>
          <el-tag :type="statusTypeMap[paper?.status] || 'info'">{{ statusLabel(paper?.status) }}</el-tag>
        </div>
        <el-tag effect="dark" class="model-tag">模型：{{ systemStore.info.llm_model_name }}</el-tag>
      </div>

      <div class="guide-strip">
        <strong>推荐阅读顺序：</strong>先看“核心思路” -> 再看“改进建议” -> 最后在右下角继续追问。
      </div>

      <el-tabs v-model="activeTab" @tab-change="loadContent">
        <el-tab-pane label="全文翻译" name="translation" />
        <el-tab-pane label="核心思路（清华模板）" name="summary" />
        <el-tab-pane label="改进建议" name="improvement" />
      </el-tabs>

      <el-skeleton :loading="contentLoading" animated :rows="10">
        <article class="markdown-body" v-html="renderMarkdown(contents[activeTab])"></article>
      </el-skeleton>
    </section>

    <aside class="chat-panel">
      <h3>论文问答助手</h3>
      <p class="chat-subtitle">当前模型：{{ systemStore.info.llm_model_name }}</p>
      <div class="chat-box">
        <div v-for="(item, idx) in messages" :key="idx" :class="['message', item.role]">
          <div class="message-role">{{ item.role === 'user' ? '你' : 'Agent' }}</div>
          <pre class="message-text">{{ item.text }}</pre>
        </div>
      </div>
      <div class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          placeholder="例如：这篇论文的方法局限在哪里？"
        />
        <el-button type="primary" :loading="sending" @click="sendQuestion">发送</el-button>
      </div>
    </aside>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import MarkdownIt from "markdown-it";

import { API_BASE_URL, askPaper, getPaperContent } from "../api/client";
import { usePaperStore } from "../stores/papers";
import { useSystemStore } from "../stores/system";

const md = new MarkdownIt({ html: false, breaks: true, linkify: true });

const route = useRoute();
const store = usePaperStore();
const systemStore = useSystemStore();

const paper = ref(null);
const activeTab = ref("translation");
const contentLoading = ref(false);
const contents = reactive({
  translation: "",
  summary: "",
  improvement: ""
});

const question = ref("");
const sending = ref(false);
const messages = ref([]);

const statusTypeMap = {
  completed: "success",
  processing: "warning",
  failed: "danger"
};

const statusTextMap = {
  completed: "已完成",
  processing: "处理中",
  failed: "处理失败"
};

const statusLabel = (status) => statusTextMap[status] || status || "未知状态";

const paperId = computed(() => route.params.paperId);
const pdfUrl = computed(() => `${API_BASE_URL}/api/papers/${paperId.value}/pdf`);

const renderMarkdown = (source) => md.render(source || "_暂无内容，请稍后刷新。_");

const loadPaper = async () => {
  try {
    paper.value = await store.fetchPaper(paperId.value);
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || "加载论文失败");
    paper.value = null;
  }
};

const loadContent = async (tabName = activeTab.value) => {
  if (!paperId.value) return;
  contentLoading.value = true;
  try {
    const { data } = await getPaperContent(paperId.value, tabName);
    contents[tabName] = data.content;
  } catch (error) {
    const detail = error?.response?.data?.detail || "加载内容失败";
    ElMessage.error(detail);
  } finally {
    contentLoading.value = false;
  }
};

const sendQuestion = async () => {
  if (!question.value.trim()) return;
  const text = question.value.trim();
  messages.value.push({ role: "user", text });
  question.value = "";
  sending.value = true;
  try {
    const { data } = await askPaper(paperId.value, { question: text, top_k: 3 });
    messages.value.push({ role: "assistant", text: data.answer });
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || "提问失败");
  } finally {
    sending.value = false;
  }
};

watch(
  () => route.params.paperId,
  async () => {
    messages.value = [];
    await loadPaper();
    await loadContent("translation");
  }
);

onMounted(async () => {
  await loadPaper();
  await loadContent("translation");
  if (!systemStore.loaded) {
    await systemStore.fetchInfo();
  }
});
</script>

<style scoped>
.workspace-page {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px;
  padding-bottom: 188px;
}

.left-pane,
.right-pane {
  min-height: calc(100vh - 220px);
  background: #ffffff;
  border: 1px solid #d7e3f4;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.pane-head {
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pane-head h2 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}

.model-tag {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.guide-strip {
  margin: 12px 12px 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #edf6ff;
  border: 1px solid #cfe4ff;
  color: #1d4d8f;
  font-size: 13px;
}

.pdf-frame {
  width: 100%;
  flex: 1;
  border: 0;
  min-height: 620px;
}

.markdown-body {
  padding: 14px;
  overflow: auto;
  line-height: 1.75;
}

.chat-panel {
  position: fixed;
  right: 18px;
  bottom: 18px;
  width: min(520px, calc(100vw - 36px));
  height: 350px;
  background: linear-gradient(180deg, #0a1b34 0%, #0e2648 100%);
  color: #e2e8f0;
  border-radius: 14px;
  padding: 12px;
  border: 1px solid #27446b;
  box-shadow: 0 10px 28px rgba(2, 6, 23, 0.45);
  display: flex;
  flex-direction: column;
}

.chat-panel h3 {
  margin: 0;
}

.chat-subtitle {
  margin: 6px 0 10px;
  color: #bfdbfe;
  font-size: 12px;
}

.chat-box {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.message {
  padding: 8px;
  border-radius: 8px;
}

.message.user {
  background: rgba(30, 64, 175, 0.45);
}

.message.assistant {
  background: rgba(15, 23, 42, 0.58);
}

.message-role {
  font-size: 12px;
  color: #93c5fd;
}

.message-text {
  margin: 6px 0 0;
  white-space: pre-wrap;
  font-family: inherit;
}

.chat-input {
  display: grid;
  grid-template-columns: 1fr 96px;
  gap: 8px;
}

@media (max-width: 1100px) {
  .workspace-page {
    grid-template-columns: 1fr;
    padding-bottom: 390px;
  }

  .chat-panel {
    width: calc(100vw - 24px);
    right: 12px;
    bottom: 12px;
  }
}
</style>
