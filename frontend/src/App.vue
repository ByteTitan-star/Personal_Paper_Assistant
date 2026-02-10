<template>
  <div class="app-shell">
    <header class="top-nav">
      <div class="top-nav-inner">
        <div class="brand-wrap">
          <div class="brand">论文 Agent 助手</div>
          <div class="brand-desc">上传、翻译、总结、改进建议一体化</div>
        </div>
        <div class="model-chip">
          当前模型：{{ systemStore.info.llm_model_name }}
        </div>
        <nav class="links">
          <RouterLink to="/" class="link">上传处理</RouterLink>
          <RouterLink to="/dashboard" class="link">论文总览</RouterLink>
        </nav>
      </div>
    </header>
    <RouterView />
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { useSystemStore } from "./stores/system";

const systemStore = useSystemStore();

onMounted(() => {
  if (!systemStore.loaded) {
    systemStore.fetchInfo();
  }
});
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(8, 23, 44, 0.94);
  backdrop-filter: blur(8px);
  color: #fff;
  border-bottom: 1px solid #22395f;
}

.top-nav-inner {
  max-width: 1320px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 24px;
}

.brand-wrap {
  min-width: 220px;
}

.brand {
  font-size: 20px;
  font-weight: 700;
}

.brand-desc {
  margin-top: 2px;
  font-size: 12px;
  color: #b8c8df;
}

.model-chip {
  margin-left: auto;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid #35588a;
  background: #102b4f;
  color: #dbeafe;
  font-size: 12px;
}

.links {
  display: flex;
  gap: 12px;
}

.link {
  color: #d7e3f6;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.link.router-link-active {
  border-color: #3a5e91;
  background: #14345f;
  color: #fff;
}

@media (max-width: 1024px) {
  .top-nav-inner {
    flex-wrap: wrap;
    gap: 10px;
  }

  .model-chip {
    order: 3;
    width: 100%;
  }
}
</style>
