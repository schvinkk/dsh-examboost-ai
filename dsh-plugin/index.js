// ExamBoost AI - DSH 插件宿主半（Host）
// 借鉴 DSH 插件开发规范（DeepSeek Harness，MIT）
// 功能设计参考：dsh-plugins-exam-practice（cypher-yht，MIT）、dsh-skill-learning-coach（wanlte，MIT）
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export const name = "dsh-examboost-ai";

export function apply(ctx, config = {}) {
  const dataRoot = config.dataRoot || "$DSH_HOME/storages/dsh-examboost-ai";
  ctx.on("ready", () => {
    ensureDir(dataRoot);
    ctx.logger.info("[ExamBoost] plugin ready, dataRoot=" + dataRoot);
  });

  // 注册工具（借鉴 exam_practice_bank 工具设计，cypher-yht，MIT）
  ctx.tool("examboost_status", {
    description: "查看 ExamBoost 学习状态与进度",
    async call() {
      const stateFile = join(dataRoot, "state.json");
      if (existsSync(stateFile)) {
        return { ok: true, data: JSON.parse(readFileSync(stateFile, "utf-8")) };
      }
      return { ok: true, data: { initialized: true, courses: 0, cards: 0 } };
    },
  });

  ctx.tool("examboost_save", {
    description: "保存学习状态到本地",
    async call(params) {
      const stateFile = join(dataRoot, "state.json");
      writeFileSync(stateFile, JSON.stringify(params, null, 2));
      return { ok: true, saved: true, path: stateFile };
    },
  });

  // 只读 HTTP 接口（loopback）
  ctx.http?.get?.("/examboost/api/health", () => ({ ok: true, app: "dsh-examboost-ai" }));
  ctx.http?.get?.("/examboost/api/state", () => {
    const stateFile = join(dataRoot, "state.json");
    return existsSync(stateFile)
      ? { ok: true, data: JSON.parse(readFileSync(stateFile, "utf-8")) }
      : { ok: true, data: {} };
  });
}

function ensureDir(dir) {
  try {
    mkdirSync(dir, { recursive: true });
  } catch (e) {
    /* ignore */
  }
}
