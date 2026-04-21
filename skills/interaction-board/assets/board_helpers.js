    function displayRefs(node) {
      return node.card?.images?.length ? node.card.images : (node.screenshot_refs || []);
    }

    function formatStatus(node) {
      return node.status === "candidate" ? "候选页" : node.status === "draft" ? "草稿页" : "已注册";
    }

    function groupLabel(group) {
      return GROUP_LABELS[group] || group || "未分组";
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
      }[char]));
    }

    function repoRelativePath(value) {
      const raw = String(value || "");
      const repoRoot = String(data.project?.repo_root || "");
      if (repoRoot && raw.startsWith(repoRoot + "/")) {
        return raw.slice(repoRoot.length + 1);
      }
      return raw;
    }

    function refDisplayPath(ref) {
      return ref?.relative_path || ref?.path || ref?.source_path || "n/a";
    }

    function uniqueImageRefs(node) {
      const seen = new Set();
      return displayRefs(node).filter((ref) => {
        const key = `${refDisplayPath(ref)}::${ref?.label || ""}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    }

    function versionLabel(count) {
      return count > 1 ? `${count} 个版本` : "1 个版本";
    }

    function scenarioStats(node) {
      return node.card?.scenario_ref_stats || {
        all_count: (node.card?.scenario_refs || []).length,
        visible_count: (node.card?.scenario_refs || []).length,
        hidden_count: 0,
        entry_count: 0,
      };
    }

    function scenarioSummary(node) {
      const stats = scenarioStats(node);
      const visible = stats.visible_count || 0;
      const hidden = stats.hidden_count || 0;
      if (!visible && !hidden) return "暂无自动化场景";
      if (hidden > 0) return `${visible} 个主场景 + ${hidden} 个入口关联`;
      return `${visible} 个自动化场景`;
    }

    function shotBadgeText(node, shot, screenshotCount) {
      if (!shot || !shot.exists) {
        return node.status === "draft" ? "AI 草图" : "待补截图";
      }
      return screenshotCount > 1 ? `已挂载快照 · ${versionLabel(screenshotCount)}` : "已挂载快照";
    }

    function readableImageLabel(ref) {
      const label = String(ref?.label || "").toLowerCase();
      if (!label || label === "planned") return "待补截图";
      if (label.startsWith("scenario:")) return "场景截图";
      if (label.includes("preview")) return "预览截图";
      if (label.includes("fidelity")) return "当前截图";
      if (label.includes("smoke")) return "运行截图";
      if (label.includes("compare") || label.includes("style-pass") || label.includes("gq-")) return "历史版本";
      return "页面截图";
    }

    function primaryShot(node) {
      const primary = node.card?.primary_image;
      if (primary?.relative_path) {
        return {
          label: primary.label,
          path: primary.relative_path,
          exists: primary.exists,
          source_path: primary.source_path,
          matched_by: primary.matched_by,
        };
      }
      const refs = displayRefs(node);
      return refs.find((item) => item.exists) || refs[0] || null;
    }

    function nodeSearchText(node) {
      const codeEntry = node.card?.code_entry || {};
      const codeAnchors = node.card?.code_anchors || node.source_refs || [];
      return [
        node.title,
        node.route,
        node.route_key,
        node.group,
        node.package,
        codeEntry.screen_component || node.screen_component,
        codeEntry.page_file || node.page_file,
        codeEntry.config_file || node.config_file,
        node.board_meta?.note,
        ...(node.board_meta?.tags || []),
        ...(node.card?.scenario_refs || []).map((ref) => ref.scenario_id || ref.script_path),
        ...(displayRefs(node) || []).flatMap((ref) => [ref.label, ref.relative_path, ref.source_path]),
        ...codeAnchors.flatMap((ref) => [ref.path, ref.line]),
        ...(node.aliases || []),
      ].join(" ").toLowerCase();
    }
