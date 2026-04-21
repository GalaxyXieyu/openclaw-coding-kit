    window.InteractionBoard.register("viewport", (ctx) => {
      let panState = null;
      let bound = false;

      function computeLaneMetrics() {
        const gutter = 36;
        const groupCount = Math.max(1, ctx.graph.orderedGroups.length);
        const frameWidth = Math.max(ctx.elements.frame?.clientWidth || 0, window.innerWidth || 0);
        const calculatedGap = groupCount > 1
          ? Math.floor((frameWidth - gutter * 2 - ctx.metrics.nodeWidth) / (groupCount - 1))
          : 0;
        return {
          left: gutter,
          gap: Math.max(ctx.metrics.laneMinGap, calculatedGap),
        };
      }

      function defaultPositions() {
        const metrics = computeLaneMetrics();
        const positions = {};
        ctx.graph.orderedGroups.forEach((group, groupIndex) => {
          ctx.graph.grouped[group].forEach((node, nodeIndex) => {
            const offsetX = ((nodeIndex + groupIndex) % 2 === 0 ? 14 : -14) + ((nodeIndex % 3) - 1) * 4;
            const offsetY = (groupIndex % 2) * 12 + (nodeIndex % 3) * 6;
            positions[node.node_id] = {
              x: metrics.left + groupIndex * metrics.gap + offsetX,
              y: ctx.metrics.lanePaddingTop + nodeIndex * ctx.metrics.nodeGapY + offsetY,
            };
          });
        });
        return positions;
      }

      function applyScale() {
        const width = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--canvas-width")) || 0;
        const height = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--canvas-height")) || 0;
        const scaledWidth = width * ctx.state.scale;
        const scaledHeight = height * ctx.state.scale;
        ctx.elements.viewport.style.width = `${scaledWidth}px`;
        ctx.elements.viewport.style.height = `${scaledHeight}px`;
        ctx.elements.stage.style.transform = `scale(${ctx.state.scale})`;
      }

      function ensureCanvasBounds() {
        const metrics = computeLaneMetrics();
        const laneRight = metrics.left + Math.max(0, ctx.graph.orderedGroups.length - 1) * metrics.gap + ctx.metrics.laneWidth;
        const positions = ctx.controllers.store.visibleNodes()
          .map((node) => ctx.state.positions[node.node_id])
          .filter(Boolean);
        const maxX = positions.reduce((acc, item) => Math.max(acc, item.x), 0);
        const maxY = positions.reduce((acc, item) => Math.max(acc, item.y), 0);
        const width = Math.max(960, laneRight + 92, maxX + ctx.metrics.nodeWidth + 96);
        const height = Math.max(860, maxY + ctx.metrics.nodeHeight + 132);
        document.documentElement.style.setProperty("--canvas-width", width + "px");
        document.documentElement.style.setProperty("--canvas-height", height + "px");
        ctx.elements.edgeLayer.setAttribute("viewBox", `0 0 ${width} ${height}`);
        applyScale();
      }

      function setScale(nextScale, anchorX, anchorY) {
        const bounded = Math.min(ctx.metrics.maxScale, Math.max(ctx.metrics.minScale, nextScale));
        if (Math.abs(bounded - ctx.state.scale) < 0.001) return;
        const previousScale = ctx.state.scale;
        const pointerX = anchorX ?? ctx.elements.frame.clientWidth / 2;
        const pointerY = anchorY ?? ctx.elements.frame.clientHeight / 2;
        const contentX = (ctx.elements.frame.scrollLeft + pointerX) / previousScale;
        const contentY = (ctx.elements.frame.scrollTop + pointerY) / previousScale;
        ctx.state.scale = bounded;
        applyScale();
        ctx.elements.frame.scrollLeft = contentX * bounded - pointerX;
        ctx.elements.frame.scrollTop = contentY * bounded - pointerY;
        ctx.controllers.store.saveScale();
      }

      function centerNode(nodeId) {
        const element = ctx.state.nodeElements.get(nodeId);
        if (!element) return;
        const position = ctx.state.positions[nodeId];
        if (!position) return;
        ctx.elements.frame.scrollTo({
          left: Math.max(0, position.x - ctx.elements.frame.clientWidth / 2 + ctx.metrics.nodeWidth / 2),
          top: Math.max(0, position.y - ctx.elements.frame.clientHeight / 2 + ctx.metrics.nodeHeight / 2),
          behavior: "smooth",
        });
      }

      function bindPanAndZoom() {
        if (bound) return;
        bound = true;
        ctx.elements.frame.addEventListener("pointerdown", (event) => {
          if (event.target.closest("button, a, input, textarea, select, summary, [role='button'], [data-no-pan='true']")) return;
          panState = {
            x: event.clientX,
            y: event.clientY,
            left: ctx.elements.frame.scrollLeft,
            top: ctx.elements.frame.scrollTop,
          };
          ctx.elements.frame.setPointerCapture(event.pointerId);
        });
        ctx.elements.frame.addEventListener("pointermove", (event) => {
          if (!panState) return;
          ctx.elements.frame.scrollLeft = panState.left - (event.clientX - panState.x);
          ctx.elements.frame.scrollTop = panState.top - (event.clientY - panState.y);
        });
        ctx.elements.frame.addEventListener("pointerup", (event) => {
          if (!panState) return;
          panState = null;
          ctx.elements.frame.releasePointerCapture(event.pointerId);
        });

        ctx.elements.frame.addEventListener("wheel", (event) => {
          if (ctx.elements.modal.open || ctx.elements.searchDialog.open) return;
          event.preventDefault();
          const factor = Math.exp(-event.deltaY * 0.0012);
          const rect = ctx.elements.frame.getBoundingClientRect();
          setScale(ctx.state.scale * factor, event.clientX - rect.left, event.clientY - rect.top);
        }, { passive: false });
      }

      return {
        computeLaneMetrics,
        defaultPositions,
        applyScale,
        ensureCanvasBounds,
        setScale,
        centerNode,
        bindPanAndZoom,
      };
    });
