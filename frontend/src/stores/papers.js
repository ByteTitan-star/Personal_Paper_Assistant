import { defineStore } from "pinia";
import { getPaperById, listPapers } from "../api/client";

export const usePaperStore = defineStore("papers", {
  state: () => ({
    papers: [],
    loading: false
  }),
  actions: {
    async fetchPapers() {
      this.loading = true;
      try {
        const { data } = await listPapers();
        this.papers = data;
      } finally {
        this.loading = false;
      }
    },
    async fetchPaper(paperId) {
      const { data } = await getPaperById(paperId);
      const existing = this.papers.find((item) => item.paper_id === paperId);
      if (existing) {
        Object.assign(existing, data);
      } else {
        this.papers.unshift(data);
      }
      return data;
    }
  }
});
