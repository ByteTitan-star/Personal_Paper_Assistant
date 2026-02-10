import { defineStore } from "pinia";
import { getSystemInfo } from "../api/client";

export const useSystemStore = defineStore("system", {
  state: () => ({
    info: {
      app_name: "Personal Scholar Agent API",
      model_provider: "LocalRuleEngine",
      llm_model_name: "DemoPipeline-v1",
      embedding_model_name: "TokenOverlapRetriever-v1",
      pipeline_mode: "DeterministicDraft"
    },
    loaded: false
  }),
  actions: {
    async fetchInfo() {
      try {
        const { data } = await getSystemInfo();
        this.info = data;
      } finally {
        this.loaded = true;
      }
    }
  }
});
