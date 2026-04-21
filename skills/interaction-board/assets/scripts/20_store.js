    window.InteractionBoard.register("store", (ctx) => {
      function loadPositions() {
        try {
          const raw = window.localStorage.getItem(ctx.constants.storageKey);
          if (!raw) return ctx.controllers.viewport.defaultPositions();
          return { ...ctx.controllers.viewport.defaultPositions(), ...JSON.parse(raw) };
        } catch {
          return ctx.controllers.viewport.defaultPositions();
        }
      }

      function loadScale() {
        try {
          const raw = Number(window.localStorage.getItem(ctx.constants.scaleStorageKey) || "1");
          if (!Number.isFinite(raw)) return 1;
          return Math.min(ctx.metrics.maxScale, Math.max(ctx.metrics.minScale, raw));
        } catch {
          return 1;
        }
      }

      function createInitialState() {
        return {
          positions: loadPositions(),
          scale: loadScale(),
          nodeElements: new Map(),
          highlightedNode: "",
          dragging: null,
          filter: "",
          pan: null,
          maxVisibleLevel: ctx.constants.defaultVisibleLevel,
          expandedGroups: new Set(),
        };
      }

      function savePositions() {
        window.localStorage.setItem(ctx.constants.storageKey, JSON.stringify(ctx.state.positions));
      }

      function saveScale() {
        window.localStorage.setItem(ctx.constants.scaleStorageKey, String(ctx.state.scale));
      }

      function isGroupExpanded(group) {
        return ctx.state.expandedGroups.has(group);
      }

      function isNodeVisible(node) {
        if (!ctx.constants.layeredCanvasEnabled) return true;
        if (ctx.controllers.helpers.nodeHierarchyLevel(node) <= ctx.state.maxVisibleLevel) return true;
        return isGroupExpanded(node.group);
      }

      function visibleNodes() {
        return ctx.data.nodes.filter((node) => isNodeVisible(node));
      }

      function visibleNodeIds() {
        return new Set(visibleNodes().map((node) => node.node_id));
      }

      function groupVisibleCount(group) {
        return (ctx.graph.grouped[group] || []).filter((node) => isNodeVisible(node)).length;
      }

      function groupHiddenCount(group) {
        return Math.max(0, (ctx.graph.grouped[group] || []).length - groupVisibleCount(group));
      }

      function ensureNodeVisible(node) {
        if (!node || isNodeVisible(node)) return false;
        ctx.state.expandedGroups.add(node.group);
        ctx.controllers.renderer.renderBoard();
        return true;
      }

      function toggleGroupExpansion(group) {
        if (!ctx.constants.layeredCanvasEnabled) return;
        if (!ctx.graph.grouped[group]?.length) return;
        if (!groupHiddenCount(group) && !isGroupExpanded(group)) return;
        if (isGroupExpanded(group)) ctx.state.expandedGroups.delete(group);
        else ctx.state.expandedGroups.add(group);
        ctx.controllers.renderer.renderBoard();
      }

      function nodeMatchesFilter(node) {
        if (!ctx.state.filter) return true;
        return ctx.controllers.helpers.nodeSearchText(node).includes(ctx.state.filter);
      }

      function filteredNodes() {
        const query = ctx.state.filter;
        const nodes = ctx.data.nodes.filter((node) => nodeMatchesFilter(node));
        return nodes.sort((left, right) => {
          if (!query) return left.title.localeCompare(right.title, "zh-CN");
          const leftText = ctx.controllers.helpers.nodeSearchText(left);
          const rightText = ctx.controllers.helpers.nodeSearchText(right);
          const leftIndex = leftText.indexOf(query);
          const rightIndex = rightText.indexOf(query);
          return (
            (leftIndex === -1 ? 9999 : leftIndex) - (rightIndex === -1 ? 9999 : rightIndex)
            || left.title.length - right.title.length
            || left.title.localeCompare(right.title, "zh-CN")
          );
        });
      }

      function resetLayout() {
        window.localStorage.removeItem(ctx.constants.storageKey);
        window.localStorage.removeItem(ctx.constants.scaleStorageKey);
        ctx.state.positions = ctx.controllers.viewport.defaultPositions();
        ctx.state.scale = 1;
        ctx.state.expandedGroups.clear();
      }

      return {
        createInitialState,
        savePositions,
        saveScale,
        isGroupExpanded,
        isNodeVisible,
        visibleNodes,
        visibleNodeIds,
        groupVisibleCount,
        groupHiddenCount,
        ensureNodeVisible,
        toggleGroupExpansion,
        nodeMatchesFilter,
        filteredNodes,
        resetLayout,
      };
    });
