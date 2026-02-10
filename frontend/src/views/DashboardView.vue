<template>
  <main class="container dashboard-page">
    <section class="main-column">
      <div class="page-head">
        <h1 class="page-title">论文总览</h1>
        <p class="head-subtitle">集中查看所有处理过的论文，按标题和领域快速筛选。</p>
      </div>

      <el-card class="filter-card" shadow="never">
        <div class="filters">
          <el-input v-model="keyword" placeholder="按标题搜索..." clearable />
          <el-select v-model="tagFilter" clearable placeholder="按领域筛选">
            <el-option v-for="tag in allTags" :key="tag" :label="tag" :value="tag" />
          </el-select>
          <el-button :loading="store.loading" @click="store.fetchPapers()">刷新</el-button>
        </div>
      </el-card>

      <el-empty v-if="filteredPapers.length === 0" description="暂无论文数据" />

      <div class="grid">
        <el-card v-for="paper in filteredPapers" :key="paper.paper_id" class="paper-card" shadow="hover">
          <h3 class="title">{{ paper.title }}</h3>
          <p class="meta"><strong>文件名：</strong>{{ paper.source_filename }}</p>
          <p class="meta"><strong>目标语言：</strong>{{ paper.target_language }}</p>
          <p class="meta"><strong>创建时间：</strong>{{ formatTime(paper.created_at) }}</p>
          <div class="tags">
            <el-tag v-for="tag in paper.domain_tags" :key="`${paper.paper_id}-${tag}`" size="small" effect="plain">
              {{ tag }}
            </el-tag>
          </div>
          <div class="foot">
            <el-tag :type="statusTypeMap[paper.status] || 'info'">{{ statusLabel(paper.status) }}</el-tag>
            <el-button type="primary" size="small" @click="goWorkspace(paper.paper_id)">
              进入工作台
            </el-button>
          </div>
        </el-card>
      </div>
    </section>

    <SystemGuidePanel class="side-column" :info="systemStore.info" />
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { usePaperStore } from "../stores/papers";
import { useSystemStore } from "../stores/system";
import SystemGuidePanel from "../components/SystemGuidePanel.vue";

const router = useRouter();
const store = usePaperStore();
const systemStore = useSystemStore();

const keyword = ref("");
const tagFilter = ref("");

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

const statusLabel = (status) => statusTextMap[status] || status;

const allTags = computed(() => {
  const values = new Set();
  for (const paper of store.papers) {
    for (const tag of paper.domain_tags || []) {
      values.add(tag);
    }
  }
  return [...values];
});

const filteredPapers = computed(() =>
  store.papers.filter((paper) => {
    const matchesKeyword = paper.title.toLowerCase().includes(keyword.value.trim().toLowerCase());
    const matchesTag = !tagFilter.value || (paper.domain_tags || []).includes(tagFilter.value);
    return matchesKeyword && matchesTag;
  })
);

const goWorkspace = (paperId) => {
  router.push(`/workspace/${paperId}`);
};

const formatTime = (iso) => new Date(iso).toLocaleString();

onMounted(async () => {
  await store.fetchPapers();
  if (!systemStore.loaded) {
    await systemStore.fetchInfo();
  }
});
</script>

<style scoped>
.dashboard-page {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 18px;
}

.main-column {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.head-subtitle {
  margin-top: 8px;
  color: #475569;
}

.filter-card {
  border-radius: 14px;
  border: 1px solid #d3def1;
}

.filters {
  display: grid;
  grid-template-columns: 1fr 250px 110px;
  gap: 10px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 14px;
}

.paper-card {
  min-height: 230px;
  border-radius: 12px;
  border: 1px solid #dae5f6;
}

.title {
  margin: 0 0 10px;
  font-size: 18px;
  color: #0f172a;
}

.meta {
  margin: 4px 0;
  color: #334155;
  font-size: 13px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.foot {
  margin-top: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 1100px) {
  .dashboard-page {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .filters {
    grid-template-columns: 1fr;
  }
}
</style>
