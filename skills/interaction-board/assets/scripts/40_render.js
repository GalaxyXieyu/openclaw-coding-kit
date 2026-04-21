    window.InteractionBoard.register("render", (ctx) => {
      function lanesMarkup() {
        const laneMetrics = ctx.controllers.viewport.computeLaneMetrics();
        return ctx.graph.orderedGroups.map((group, index) => {
          const left = laneMetrics.left - 6 + index * laneMetrics.gap;
          const totalCount = ctx.graph.grouped[group].length;
          const visibleCount = ctx.controllers.store.groupVisibleCount(group);
          const hiddenCount = ctx.controllers.store.groupHiddenCount(group);
          const expanded = ctx.controllers.store.isGroupExpanded(group);
          const label = ctx.constants.layeredCanvasEnabled
            ? `${visibleCount} / ${totalCount} 页`
            : `${totalCount} 页`;
          const action = ctx.constants.layeredCanvasEnabled && (hiddenCount > 0 || expanded)
            ? `<span class="lane-action">${expanded ? "收起深层" : `展开 ${hiddenCount}`}</span>`
            : "";
          return `
          <section class="lane" style="left:${left}px;width:${ctx.metrics.laneWidth}px;">
            <button
              type="button"
              class="lane-label ${hiddenCount > 0 || expanded ? "expandable" : ""} ${expanded ? "expanded" : ""}"
              data-group="${group}"
              aria-pressed="${expanded ? "true" : "false"}"
            >
              <strong>${ctx.controllers.helpers.groupLabel(group)}</strong>
              <small>${label}</small>
              ${action}
            </button>
          </section>
        `;
        }).join("");
      }

      function buildNodeCard(node) {
        const shot = ctx.controllers.helpers.primaryShot(node);
        const screenshotCount = ctx.controllers.helpers.displayRefs(node).filter((item) => item.exists).length;
        const placeholderLabel = node.status === "draft" ? "AI 草图" : "待截图";
        const button = document.createElement("button");
        button.type = "button";
        button.className = `node ${node.status}`;
        button.dataset.nodeId = node.node_id;
        button.dataset.group = node.group;
        button.style.left = ctx.state.positions[node.node_id].x + "px";
        button.style.top = ctx.state.positions[node.node_id].y + "px";
        button.setAttribute("aria-label", `${node.title} · ${ctx.controllers.helpers.formatStatus(node)} · ${node.route}`);
        button.innerHTML = `
        <div class="node-shot ${shot && shot.exists ? "has-shot" : "missing-shot"}">
          ${shot && shot.exists ? `<img src="${shot.path}" alt="${node.title}" loading="lazy" />` : ""}
          ${shot && shot.exists ? "" : `<span class="node-shot-grid" aria-hidden="true"></span><span class="node-empty-badge">${placeholderLabel}</span>`}
          <div class="node-overlay">
            <span class="node-title-wrap">
              <span class="node-title">${node.title}</span>
              <span class="node-subtitle">${ctx.controllers.helpers.shotBadgeText(node, shot, screenshotCount)}</span>
            </span>
          </div>
        </div>
      `;

        button.addEventListener("mouseenter", (event) => showTooltip(node, event, button));
        button.addEventListener("mousemove", (event) => moveTooltip(event));
        button.addEventListener("mouseleave", () => hideTooltip());
        button.addEventListener("focus", () => showTooltip(node, null, button));
        button.addEventListener("blur", () => hideTooltip());
        button.addEventListener("click", () => {
          if (button.dataset.dragMoved === "true") {
            button.dataset.dragMoved = "false";
            return;
          }
          ctx.controllers.modal.openNodeModal(node);
        });
        button.addEventListener("pointerdown", (event) => ctx.controllers.interactions.startDrag(event, node, button));
        return button;
      }

      function renderNodes() {
        ctx.elements.stage.innerHTML = lanesMarkup();
        ctx.elements.stage.appendChild(ctx.elements.edgeLayer);
        ctx.state.nodeElements.clear();
        ctx.controllers.store.visibleNodes().forEach((node) => {
          const element = buildNodeCard(node);
          ctx.state.nodeElements.set(node.node_id, element);
          ctx.elements.stage.appendChild(element);
        });
        bindLaneActions();
        ctx.controllers.viewport.ensureCanvasBounds();
        renderEdges();
        applyFilter();
      }

      function bindLaneActions() {
        ctx.elements.stage.querySelectorAll(".lane-label[data-group]").forEach((button) => {
          button.addEventListener("pointerdown", (event) => {
            event.stopPropagation();
          });
          button.addEventListener("click", () => {
            ctx.controllers.store.toggleGroupExpansion(button.dataset.group);
          });
        });
      }

      function renderBoard(options = {}) {
        const { preserveScroll = true } = options;
        const previousLeft = ctx.elements.frame.scrollLeft;
        const previousTop = ctx.elements.frame.scrollTop;
        renderNodes();
        ctx.controllers.search.renderSearchResults();
        if (preserveScroll) {
          ctx.elements.frame.scrollLeft = previousLeft;
          ctx.elements.frame.scrollTop = previousTop;
        }
      }

      function edgePath(from, to, index, total) {
        const spread = (index - (total - 1) / 2) * 22;
        const startX = from.x + ctx.metrics.nodeWidth - 4;
        const startY = from.y + ctx.metrics.nodeHeight * 0.5 + spread * 0.34;
        const endX = to.x + 4;
        const endY = to.y + ctx.metrics.nodeHeight * 0.5 - spread * 0.34;
        const bend = Math.max(92, Math.abs(endX - startX) * 0.42);
        const lift = spread * 0.9;
        return `M ${startX} ${startY} C ${startX + bend} ${startY + lift}, ${endX - bend} ${endY - lift}, ${endX} ${endY}`;
      }

      function renderEdges() {
        ctx.elements.edgeLayer.querySelectorAll("path.edge-line").forEach((item) => item.remove());
        const activeNode = ctx.state.highlightedNode;
        const visibleIds = ctx.controllers.store.visibleNodeIds();
        const pairMap = new Map();
        ctx.data.edges.forEach((edge) => {
          if (!visibleIds.has(edge.from) || !visibleIds.has(edge.to)) return;
          const key = `${edge.from}->${edge.to}`;
          const group = pairMap.get(key) || [];
          group.push(edge);
          pairMap.set(key, group);
        });

        Array.from(pairMap.entries()).forEach(([pairKey, group]) => {
          const [edge] = group;
          const from = ctx.state.positions[edge.from];
          const to = ctx.state.positions[edge.to];
          if (!from || !to) return;
          const index = 0;
          const edgeMatched = !ctx.state.filter || ctx.controllers.store.nodeMatchesFilter(ctx.graph.nodeById.get(edge.from)) || ctx.controllers.store.nodeMatchesFilter(ctx.graph.nodeById.get(edge.to));
          const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
          path.setAttribute("d", edgePath(from, to, index, group.length));
          path.setAttribute(
            "class",
            `edge-line kind-${edge.kind} ${activeNode && (edge.from === activeNode || edge.to === activeNode) ? "active" : ""} ${edgeMatched ? "" : "muted"}`
          );
          path.dataset.edgePair = pairKey;
          path.dataset.edgeCount = String(group.length);
          path.setAttribute("marker-end", "url(#edgeArrow)");
          ctx.elements.edgeLayer.appendChild(path);
        });
      }

      function setHighlight(nodeId) {
        ctx.state.highlightedNode = nodeId || "";
        ctx.state.nodeElements.forEach((element, currentId) => {
          element.classList.toggle("active", currentId === ctx.state.highlightedNode);
        });
        renderEdges();
      }

      function showTooltip(node, event, element) {
        const outgoing = ctx.data.edges.filter((edge) => edge.from === node.node_id).length;
        const incoming = ctx.data.edges.filter((edge) => edge.to === node.node_id).length;
        const codeEntry = node.card?.code_entry || {};
        const codeAnchors = node.card?.code_anchors?.length ? node.card.code_anchors : (node.source_refs || []);
        const firstRef = codeAnchors[0];
        const shot = ctx.controllers.helpers.primaryShot(node);
        const screenshotCount = ctx.controllers.helpers.displayRefs(node).filter((item) => item.exists).length;
        const note = node.board_meta?.note;
        ctx.elements.tooltip.innerHTML = `
        <strong>${node.title}</strong>
        <code>${node.route}</code>
        <div class="tooltip-grid">
          <span>${ctx.controllers.helpers.formatStatus(node)} · ${ctx.controllers.helpers.groupLabel(node.group)}</span>
          <span>${screenshotCount ? `${screenshotCount} 个版本快照` : "暂无真实截图"}</span>
          <span>${ctx.controllers.helpers.scenarioSummary(node)}</span>
          <span>流出 ${outgoing}</span>
          <span>流入 ${incoming}</span>
        </div>
        <div style="margin-top:10px;font-size:12px;color:rgba(255,255,255,0.82);line-height:1.6;">
          组件：${codeEntry.screen_component || node.screen_component || "未解析"}<br />
          锚点：${firstRef ? `${firstRef.path}:${firstRef.line}` : "n/a"}<br />
          主图：${shot?.path || "n/a"}${shot?.matched_by ? `<br />匹配：${shot.matched_by}` : ""}
          ${note ? `<br />备注：${note}` : ""}
        </div>
      `;
        ctx.elements.tooltip.classList.add("visible");
        ctx.elements.tooltip.setAttribute("aria-hidden", "false");
        if (event) {
          moveTooltip(event);
        } else {
          const rect = element.getBoundingClientRect();
          moveTooltip({ clientX: rect.right - 20, clientY: rect.top + 20 });
        }
        setHighlight(node.node_id);
      }

      function moveTooltip(event) {
        const offsetX = 18;
        const offsetY = 18;
        const maxX = window.innerWidth - ctx.elements.tooltip.offsetWidth - 12;
        const maxY = window.innerHeight - ctx.elements.tooltip.offsetHeight - 12;
        const x = Math.min(maxX, event.clientX + offsetX);
        const y = Math.min(maxY, event.clientY + offsetY);
        ctx.elements.tooltip.style.left = `${Math.max(12, x)}px`;
        ctx.elements.tooltip.style.top = `${Math.max(12, y)}px`;
      }

      function hideTooltip() {
        ctx.elements.tooltip.classList.remove("visible");
        ctx.elements.tooltip.setAttribute("aria-hidden", "true");
        if (!ctx.elements.modal.open) setHighlight("");
      }

      function applyFilter() {
        ctx.state.nodeElements.forEach((element, nodeId) => {
          const node = ctx.graph.nodeById.get(nodeId);
          if (!node) return;
          element.classList.toggle("dim", !ctx.controllers.store.nodeMatchesFilter(node));
        });
        renderEdges();
      }

      return {
        renderBoard,
        renderNodes,
        renderEdges,
        setHighlight,
        showTooltip,
        moveTooltip,
        hideTooltip,
        applyFilter,
      };
    });
