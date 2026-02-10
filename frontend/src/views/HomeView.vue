<template>
  <main class="container home-page">
    <section class="main-column">
      <div class="hero">
        <h1 class="page-title">上传论文并启动 Agent 流程</h1>
        <p class="hero-subtitle">
          上传后系统会自动执行：解析 -> 翻译 -> 核心思路总结 -> 改进建议生成。
        </p>
      </div>

      <el-card class="upload-card" shadow="hover">
        <el-form :inline="true" class="config-form">
          <el-form-item label="目标语言">
            <el-select v-model="targetLanguage" style="width: 180px">
              <el-option label="中文" value="中文" />
              <el-option label="英文" value="英文" />
              <el-option label="日文" value="日文" />
            </el-select>
          </el-form-item>
          <el-form-item label="总结模板">
            <el-select v-model="summaryTemplate" style="width: 220px">
              <el-option
                v-for="template in templates"
                :key="template.name"
                :label="template.name"
                :value="template.name"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <el-upload drag :limit="1" accept=".pdf" :http-request="onUploadRequest">
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将 PDF 拖到此处，或点击上传</div>
          <template #tip>
            <div class="el-upload__tip">仅支持 `.pdf` 文件，建议优先上传文本版论文。</div>
          </template>
        </el-upload>

        <div class="progress-box" v-if="taskId">
          <div class="progress-header">
            <strong>任务状态：</strong>{{ statusText }}
          </div>
          <el-progress :percentage="progress" :status="progressStatus" :stroke-width="16" />
        </div>

        <div class="actions">
          <el-button type="primary" :disabled="!paperId || progress < 100" @click="goWorkspace">
            打开阅读工作台
          </el-button>
          <el-button @click="$router.push('/dashboard')">查看论文总览</el-button>
        </div>
      </el-card>
    </section>

    <SystemGuidePanel class="side-column" :info="systemStore.info" />
  </main>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { UploadFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import { API_BASE_URL, listTemplates, uploadPaper } from "../api/client";
import { usePaperStore } from "../stores/papers";
import { useSystemStore } from "../stores/system";
import SystemGuidePanel from "../components/SystemGuidePanel.vue";

const router = useRouter();
const store = usePaperStore();
const systemStore = useSystemStore();

const targetLanguage = ref("中文");
const summaryTemplate = ref("tinghua.md");
const templates = ref([{ name: "tinghua.md" }]);

const taskId = ref("");
const paperId = ref("");
const progress = ref(0);
const statusText = ref("当前无运行任务");
const progressStatus = ref("");

let eventSource = null;

const statusLabelMap = {
  queued: "排队中",
  parsing: "解析中",
  translating: "翻译中",
  summarizing: "总结中",
  critiquing: "建议生成中",
  done: "已完成",
  failed: "失败"
};

const loadTemplates = async () => {
  const { data } = await listTemplates();
  templates.value = data;
  if (!templates.value.some((item) => item.name === summaryTemplate.value) && templates.value.length > 0) {
    summaryTemplate.value = templates.value[0].name;
  }
};

const closeTaskStream = () => {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
};

const openTaskStream = (newTaskId) => {
  closeTaskStream();
  eventSource = new EventSource(`${API_BASE_URL}/api/tasks/${newTaskId}/events`);
  eventSource.addEventListener("progress", async (event) => {
    const payload = JSON.parse(event.data);
    progress.value = payload.progress;
    const statusTextRaw = statusLabelMap[payload.status] || payload.status;
    statusText.value = `${statusTextRaw}：${payload.message}`;
    if (payload.status === "failed") {
      progressStatus.value = "exception";
      ElMessage.error(payload.message);
      closeTaskStream();
      return;
    }
    if (payload.status === "done") {
      progressStatus.value = "success";
      await store.fetchPapers();
      closeTaskStream();
    }
  });
  eventSource.onerror = () => {
    closeTaskStream();
  };
};

const onUploadRequest = async ({ file, onSuccess, onError }) => {
  try {
    progress.value = 0;
    progressStatus.value = "";
    const { data } = await uploadPaper(file, targetLanguage.value, summaryTemplate.value);
    taskId.value = data.task_id;
    paperId.value = data.paper_id;
    statusText.value = "任务已创建，正在排队";
    openTaskStream(taskId.value);
    onSuccess();
  } catch (error) {
    const message = error?.response?.data?.detail || error.message || "上传失败";
    ElMessage.error(message);
    onError(error);
  }
};

const goWorkspace = () => {
  router.push(`/workspace/${paperId.value}`);
};

onMounted(async () => {
  await loadTemplates();
  await store.fetchPapers();
  if (!systemStore.loaded) {
    await systemStore.fetchInfo();
  }
});

onBeforeUnmount(() => {
  closeTaskStream();
});
</script>

<style scoped>
.home-page {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 18px;
}

.main-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero {
  background: linear-gradient(135deg, #113b78 0%, #1d4f97 55%, #3b82f6 100%);
  border-radius: 16px;
  padding: 18px 20px;
  color: #eff6ff;
  box-shadow: 0 10px 26px rgba(30, 64, 175, 0.22);
}

.hero-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: #dbeafe;
}

.upload-card {
  border-radius: 14px;
  border: 1px solid #cfddf7;
}

.config-form {
  margin-bottom: 6px;
}

.progress-box {
  margin-top: 20px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fbff;
  border: 1px solid #dbeafe;
}

.progress-header {
  margin-bottom: 10px;
  color: #1e293b;
}

.actions {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 1100px) {
  .home-page {
    grid-template-columns: 1fr;
  }
}
</style>
