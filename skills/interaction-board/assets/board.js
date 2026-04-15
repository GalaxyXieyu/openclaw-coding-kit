    const data = JSON.parse(document.getElementById("board-data").textContent);
    const GROUP_ORDER = __GROUP_ORDER__;
    const GROUP_LABELS = {
      entry: "入口",
      guiquan: "龟圈",
      products: "宠物",
      footprint: "足迹",
      account: "账号",
      public: "公开",
      candidate: "候选",
      other: "其他",
    };
    const STORAGE_KEY = "interaction-board-layout::" + (data.project?.name || "board") + "::v6";
    const SCALE_STORAGE_KEY = STORAGE_KEY + "::scale";
    const nodeWidth = 188;
    const nodeHeight = 346;
    const laneMinGap = 228;
    const laneWidth = 196;
    const lanePaddingTop = 94;
    const nodeGapY = 344;
    const minScale = 0.72;
    const maxScale = 1.6;

    const viewport = document.getElementById("boardViewport");
    const stage = document.getElementById("boardStage");
    const frame = document.getElementById("boardFrame");
    const edgeLayer = document.getElementById("edgeLayer");
    const tooltip = document.getElementById("boardTooltip");
    const modal = document.getElementById("nodeModal");
    const modalTitle = document.getElementById("modalTitle");
    const modalSubtitle = document.getElementById("modalSubtitle");
    const modalVersions = document.getElementById("modalVersions");
    const modalRegions = document.getElementById("modalRegions");
    const modalRefs = document.getElementById("modalRefs");
    const modalScenarios = document.getElementById("modalScenarios");
    const modalEdges = document.getElementById("modalEdges");
    const modalClose = document.getElementById("modalClose");

    const searchDialog = document.getElementById("searchDialog");
    const searchInput = document.getElementById("boardSearch");
    const searchResults = document.getElementById("searchResults");
    const openSearchButton = document.getElementById("openSearch");
    const closeSearchButton = document.getElementById("closeSearch");
    const togglePanelButton = document.getElementById("togglePanel");
    const resetButton = document.getElementById("resetLayout");
    const dockPanel = document.getElementById("dockPanel");

    const grouped = {};
    const nodeById = new Map();
    data.nodes.forEach((node) => {
      grouped[node.group] = grouped[node.group] || [];
      grouped[node.group].push(node);
      nodeById.set(node.node_id, node);
    });
    const orderedGroups = Object.keys(grouped).sort((a, b) => (GROUP_ORDER[a] ?? 99) - (GROUP_ORDER[b] ?? 99) || a.localeCompare(b));

    function computeLaneMetrics() {
      const gutter = 36;
      const groupCount = Math.max(1, orderedGroups.length);
      const frameWidth = Math.max(frame?.clientWidth || 0, window.innerWidth || 0);
      const calculatedGap = groupCount > 1
        ? Math.floor((frameWidth - gutter * 2 - nodeWidth) / (groupCount - 1))
        : 0;
      return {
        left: gutter,
        gap: Math.max(laneMinGap, calculatedGap),
      };
    }

    function defaultPositions() {
      const metrics = computeLaneMetrics();
      const positions = {};
      orderedGroups.forEach((group, groupIndex) => {
        grouped[group].forEach((node, nodeIndex) => {
          const offsetX = ((nodeIndex + groupIndex) % 2 === 0 ? 14 : -14) + ((nodeIndex % 3) - 1) * 4;
          const offsetY = (groupIndex % 2) * 12 + (nodeIndex % 3) * 6;
          positions[node.node_id] = {
            x: metrics.left + groupIndex * metrics.gap + offsetX,
            y: lanePaddingTop + nodeIndex * nodeGapY + offsetY,
          };
        });
      });
      return positions;
    }

    function loadPositions() {
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return defaultPositions();
        return { ...defaultPositions(), ...JSON.parse(raw) };
      } catch {
        return defaultPositions();
      }
    }

    function loadScale() {
      try {
        const raw = Number(window.localStorage.getItem(SCALE_STORAGE_KEY) || "1");
        if (!Number.isFinite(raw)) return 1;
        return Math.min(maxScale, Math.max(minScale, raw));
      } catch {
        return 1;
      }
    }

    const state = {
      positions: loadPositions(),
      scale: loadScale(),
      nodeElements: new Map(),
      highlightedNode: "",
      dragging: null,
      filter: "",
      pan: null,
    };

    function savePositions() {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state.positions));
    }

    function saveScale() {
      window.localStorage.setItem(SCALE_STORAGE_KEY, String(state.scale));
    }

    function displayRefs(node) {
      return node.card?.images?.length ? node.card.images : (node.screenshot_refs || []);
    }

    function formatStatus(node) {
      return node.status === "candidate" ? "候选页" : node.status === "draft" ? "草稿页" : "已注册";
    }

    function groupLabel(group) {
      return GROUP_LABELS[group] || group || "未分组";
    }

    function versionLabel(count) {
      return count > 1 ? `${count} 个版本` : "1 个版本";
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
      return [
        node.title,
        node.route,
        node.route_key,
        node.group,
        node.package,
        node.screen_component,
        node.board_meta?.note,
        ...(node.board_meta?.tags || []),
        ...(node.card?.scenario_refs || []).map((ref) => ref.scenario_id || ref.script_path),
        ...(displayRefs(node) || []).flatMap((ref) => [ref.label, ref.relative_path, ref.source_path]),
        ...(node.aliases || []),
      ].join(" ").toLowerCase();
    }

    function nodeMatchesFilter(node) {
      if (!state.filter) return true;
      return nodeSearchText(node).includes(state.filter);
    }

    function filteredNodes() {
      const query = state.filter;
      const nodes = data.nodes.filter((node) => nodeMatchesFilter(node));
      return nodes.sort((left, right) => {
        if (!query) return left.title.localeCompare(right.title, "zh-CN");
        const leftText = nodeSearchText(left);
        const rightText = nodeSearchText(right);
        const leftIndex = leftText.indexOf(query);
        const rightIndex = rightText.indexOf(query);
        return (
          (leftIndex === -1 ? 9999 : leftIndex) - (rightIndex === -1 ? 9999 : rightIndex)
          || left.title.length - right.title.length
          || left.title.localeCompare(right.title, "zh-CN")
        );
      });
    }

    function lanesMarkup() {
      const metrics = computeLaneMetrics();
      return orderedGroups.map((group, index) => {
        const left = metrics.left - 6 + index * metrics.gap;
        const label = grouped[group].length + " 页";
        return `<section class="lane" style="left:${left}px;width:${laneWidth}px;"><span class="lane-label"><strong>${groupLabel(group)}</strong><small>${label}</small></span></section>`;
      }).join("");
    }

    function ensureCanvasBounds() {
      const positions = Object.values(state.positions);
      const maxX = positions.reduce((acc, item) => Math.max(acc, item.x), 0);
      const maxY = positions.reduce((acc, item) => Math.max(acc, item.y), 0);
      const width = Math.max(960, maxX + nodeWidth + 96);
      const height = Math.max(860, maxY + nodeHeight + 132);
      document.documentElement.style.setProperty("--canvas-width", width + "px");
      document.documentElement.style.setProperty("--canvas-height", height + "px");
      edgeLayer.setAttribute("viewBox", `0 0 ${width} ${height}`);
      applyScale();
    }

    function applyScale() {
      const width = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--canvas-width")) || 0;
      const height = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--canvas-height")) || 0;
      const scaledWidth = width * state.scale;
      const scaledHeight = height * state.scale;
      viewport.style.width = `${scaledWidth}px`;
      viewport.style.height = `${scaledHeight}px`;
      stage.style.transform = `scale(${state.scale})`;
    }

    function setScale(nextScale, anchorX, anchorY) {
      const bounded = Math.min(maxScale, Math.max(minScale, nextScale));
      if (Math.abs(bounded - state.scale) < 0.001) return;
      const previousScale = state.scale;
      const pointerX = anchorX ?? frame.clientWidth / 2;
      const pointerY = anchorY ?? frame.clientHeight / 2;
      const contentX = (frame.scrollLeft + pointerX) / previousScale;
      const contentY = (frame.scrollTop + pointerY) / previousScale;
      state.scale = bounded;
      applyScale();
      frame.scrollLeft = contentX * bounded - pointerX;
      frame.scrollTop = contentY * bounded - pointerY;
      saveScale();
    }

    function buildNodeCard(node) {
      const shot = primaryShot(node);
      const screenshotCount = displayRefs(node).filter((item) => item.exists).length;
      const placeholderLabel = node.status === "draft" ? "AI 草图" : "待截图";
      const button = document.createElement("button");
      button.type = "button";
      button.className = `node ${node.status}`;
      button.dataset.nodeId = node.node_id;
      button.dataset.group = node.group;
      button.style.left = state.positions[node.node_id].x + "px";
      button.style.top = state.positions[node.node_id].y + "px";
      button.setAttribute("aria-label", `${node.title} · ${formatStatus(node)} · ${node.route}`);
      button.innerHTML = `
        <div class="node-shot ${shot && shot.exists ? "has-shot" : "missing-shot"}">
          ${shot && shot.exists ? `<img src="${shot.path}" alt="${node.title}" loading="lazy" />` : ""}
          ${shot && shot.exists ? "" : `<span class="node-shot-grid" aria-hidden="true"></span><span class="node-empty-badge">${placeholderLabel}</span>`}
          <div class="node-overlay">
            <span class="node-title-wrap">
              <span class="node-title">${node.title}</span>
              <span class="node-subtitle">${shotBadgeText(node, shot, screenshotCount)}</span>
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
        openNodeModal(node);
      });
      button.addEventListener("pointerdown", (event) => startDrag(event, node, button));
      return button;
    }

    function renderNodes() {
      stage.innerHTML = lanesMarkup();
      stage.appendChild(edgeLayer);
      data.nodes.forEach((node) => {
        const element = buildNodeCard(node);
        state.nodeElements.set(node.node_id, element);
        stage.appendChild(element);
      });
      ensureCanvasBounds();
      renderEdges();
      applyFilter();
    }

    function edgePath(from, to, index, total) {
      const spread = (index - (total - 1) / 2) * 22;
      const startX = from.x + nodeWidth - 4;
      const startY = from.y + nodeHeight * 0.5 + spread * 0.34;
      const endX = to.x + 4;
      const endY = to.y + nodeHeight * 0.5 - spread * 0.34;
      const bend = Math.max(92, Math.abs(endX - startX) * 0.42);
      const lift = spread * 0.9;
      return `M ${startX} ${startY} C ${startX + bend} ${startY + lift}, ${endX - bend} ${endY - lift}, ${endX} ${endY}`;
    }

    function renderEdges() {
      edgeLayer.querySelectorAll("path.edge-line").forEach((item) => item.remove());
      const activeNode = state.highlightedNode;
      const pairMap = new Map();
      data.edges.forEach((edge) => {
        const key = `${edge.from}->${edge.to}`;
        const group = pairMap.get(key) || [];
        group.push(edge);
        pairMap.set(key, group);
      });

      Array.from(pairMap.entries()).forEach(([pairKey, group]) => {
        const [edge] = group;
        const from = state.positions[edge.from];
        const to = state.positions[edge.to];
        if (!from || !to) return;
        const index = 0;
        const edgeMatched = !state.filter || nodeMatchesFilter(nodeById.get(edge.from)) || nodeMatchesFilter(nodeById.get(edge.to));
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", edgePath(from, to, index, group.length));
        path.setAttribute(
          "class",
          `edge-line kind-${edge.kind} ${activeNode && (edge.from === activeNode || edge.to === activeNode) ? "active" : ""} ${edgeMatched ? "" : "muted"}`
        );
        path.dataset.edgePair = pairKey;
        path.dataset.edgeCount = String(group.length);
        path.setAttribute("marker-end", "url(#edgeArrow)");
        edgeLayer.appendChild(path);
      });
    }

    function setHighlight(nodeId) {
      state.highlightedNode = nodeId || "";
      state.nodeElements.forEach((element, currentId) => {
        element.classList.toggle("active", currentId === state.highlightedNode);
      });
      renderEdges();
    }

    function showTooltip(node, event, element) {
      const outgoing = data.edges.filter((edge) => edge.from === node.node_id).length;
      const incoming = data.edges.filter((edge) => edge.to === node.node_id).length;
      const firstRef = node.source_refs?.[0];
      const shot = primaryShot(node);
      const screenshotCount = displayRefs(node).filter((item) => item.exists).length;
      const scenarioCount = (node.card?.scenario_refs || []).length;
      const note = node.board_meta?.note;
      tooltip.innerHTML = `
        <strong>${node.title}</strong>
        <code>${node.route}</code>
        <div class="tooltip-grid">
          <span>${formatStatus(node)} · ${groupLabel(node.group)}</span>
          <span>${screenshotCount ? `${screenshotCount} 个版本快照` : "暂无真实截图"}</span>
          <span>${scenarioCount ? `${scenarioCount} 个自动化场景` : "暂无自动化场景"}</span>
          <span>流出 ${outgoing}</span>
          <span>流入 ${incoming}</span>
        </div>
        <div style="margin-top:10px;font-size:12px;color:rgba(255,255,255,0.82);line-height:1.6;">
          组件：${node.screen_component || "未解析"}<br />
          锚点：${firstRef ? `${firstRef.path}:${firstRef.line}` : "n/a"}<br />
          主图：${shot?.path || "n/a"}${shot?.matched_by ? `<br />匹配：${shot.matched_by}` : ""}
          ${note ? `<br />备注：${note}` : ""}
        </div>
      `;
      tooltip.classList.add("visible");
      tooltip.setAttribute("aria-hidden", "false");
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
      const maxX = window.innerWidth - tooltip.offsetWidth - 12;
      const maxY = window.innerHeight - tooltip.offsetHeight - 12;
      const x = Math.min(maxX, event.clientX + offsetX);
      const y = Math.min(maxY, event.clientY + offsetY);
      tooltip.style.left = `${Math.max(12, x)}px`;
      tooltip.style.top = `${Math.max(12, y)}px`;
    }

    function hideTooltip() {
      tooltip.classList.remove("visible");
      tooltip.setAttribute("aria-hidden", "true");
      if (!modal.open) setHighlight("");
    }

    function fillList(target, items, formatter) {
      target.innerHTML = "";
      if (!items.length) {
        const li = document.createElement("li");
        li.textContent = "暂无";
        target.appendChild(li);
        return;
      }
      items.forEach((item) => {
        const li = document.createElement("li");
        li.innerHTML = formatter(item);
        target.appendChild(li);
      });
    }

    function centerNode(nodeId) {
      const position = state.positions[nodeId];
      if (!position) return;
      frame.scrollTo({
        left: Math.max(0, position.x - frame.clientWidth / 2 + nodeWidth / 2),
        top: Math.max(0, position.y - frame.clientHeight / 2 + nodeHeight / 2),
        behavior: "smooth",
      });
    }

    function openNodeModal(node) {
      const outgoing = data.edges.filter((edge) => edge.from === node.node_id);
      const incoming = data.edges.filter((edge) => edge.to === node.node_id);
      modalTitle.textContent = node.title;
      modalSubtitle.innerHTML = `<code>${node.route}</code><br />${node.screen_component || "未解析组件"}`;

      const refs = displayRefs(node);
      modalVersions.innerHTML = refs.length ? refs.map((ref) => {
        if (!ref.exists) {
          return `<article class="version-card"><div class="empty-note">待补截图<br /><code>${ref.relative_path || ref.path || "n/a"}</code></div><div class="meta"><strong>${readableImageLabel(ref)}</strong><code>${ref.relative_path || ref.path || "n/a"}</code></div></article>`;
        }
        return `
          <article class="version-card">
            <img src="${ref.relative_path || ref.path}" alt="${node.title} ${ref.label}" loading="lazy" />
            <div class="meta">
              <strong>${readableImageLabel(ref)}</strong>
              <code>${ref.relative_path || ref.path}</code>
              ${ref.matched_by ? `<code>${ref.matched_by}</code>` : ""}
              ${ref.source_path ? `<code>${ref.source_path}</code>` : ""}
            </div>
          </article>
        `;
      }).join("") : `<div class="empty-note">暂无版本快照。</div>`;

      fillList(modalRegions, node.regions || [], (item) => item);
      fillList(modalRefs, node.source_refs || [], (ref) => `<code>${ref.path}:${ref.line}</code>`);
      fillList(
        modalScenarios,
        node.card?.scenario_refs || [],
        (ref) => `<strong>${ref.scenario_id || "scenario"}</strong> · ${ref.role || "manual"}<br /><code>${ref.script_path || ref.scenario_path || "n/a"}</code>`
      );
      fillList(
        modalEdges,
        [...outgoing.map((edge) => ({ direction: "out", edge })), ...incoming.map((edge) => ({ direction: "in", edge }))],
        ({ direction, edge }) => {
          const targetId = direction === "out" ? edge.to : edge.from;
          const targetNode = nodeById.get(targetId);
          return `<strong>${direction === "out" ? "→" : "←"} ${targetNode?.title || targetId}</strong> · ${edge.kind}<br /><code>${edge.trigger}</code>`;
        }
      );

      modal.showModal();
      centerNode(node.node_id);
      setHighlight(node.node_id);
    }

    modalClose.addEventListener("click", () => {
      modal.close();
      setHighlight("");
    });

    modal.addEventListener("click", (event) => {
      const rect = modal.getBoundingClientRect();
      const inside = rect.top <= event.clientY && event.clientY <= rect.top + rect.height && rect.left <= event.clientX && event.clientX <= rect.left + rect.width;
      if (!inside) {
        modal.close();
        setHighlight("");
      }
    });
    modal.addEventListener("close", () => setHighlight(""));

    function startDrag(event, node, element) {
      if (event.button !== 0) return;
      event.preventDefault();
      const origin = state.positions[node.node_id];
      state.dragging = {
        nodeId: node.node_id,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        originX: origin.x,
        originY: origin.y,
      };
      element.dataset.dragMoved = "false";
      element.classList.add("dragging");
      element.setPointerCapture(event.pointerId);
      setHighlight(node.node_id);

      const handleMove = (moveEvent) => {
        if (!state.dragging || state.dragging.pointerId !== moveEvent.pointerId) return;
        const dx = moveEvent.clientX - state.dragging.startX;
        const dy = moveEvent.clientY - state.dragging.startY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          element.dataset.dragMoved = "true";
        }
        state.positions[node.node_id] = {
          x: Math.max(18, state.dragging.originX + dx),
          y: Math.max(18, state.dragging.originY + dy),
        };
        element.style.left = state.positions[node.node_id].x + "px";
        element.style.top = state.positions[node.node_id].y + "px";
        ensureCanvasBounds();
        renderEdges();
      };

      const handleUp = (upEvent) => {
        if (!state.dragging || state.dragging.pointerId !== upEvent.pointerId) return;
        element.classList.remove("dragging");
        element.releasePointerCapture(upEvent.pointerId);
        state.dragging = null;
        savePositions();
        renderEdges();
        window.removeEventListener("pointermove", handleMove);
        window.removeEventListener("pointerup", handleUp);
      };

      window.addEventListener("pointermove", handleMove);
      window.addEventListener("pointerup", handleUp);
    }

    function applyFilter() {
      data.nodes.forEach((node) => {
        const matched = nodeMatchesFilter(node);
        const element = state.nodeElements.get(node.node_id);
        if (element) element.classList.toggle("dim", !matched);
      });
      renderEdges();
    }

    function renderSearchResults() {
      const matches = filteredNodes().slice(0, 18);
      if (!matches.length) {
        searchResults.innerHTML = `<div class="search-empty">${state.filter ? "没有命中节点，试试路由、组件名或截图来源标签。" : "输入关键词后会显示匹配节点。"} </div>`;
        return;
      }
      searchResults.innerHTML = matches.map((node) => {
        const shot = primaryShot(node);
        const scenarios = (node.card?.scenario_refs || []).length;
        const versions = displayRefs(node).filter((item) => item.exists).length;
        return `
          <button type="button" class="search-result" data-node-id="${node.node_id}">
            <strong>${node.title}</strong>
            <code>${node.route}</code>
            <div class="search-result-meta">
              <span>${formatStatus(node)}</span>
              <span>${groupLabel(node.group)}</span>
              <span>${versions ? `${versions} 个版本` : "无快照"}</span>
              <span>${scenarios ? `${scenarios} 个场景` : "无场景"}</span>
              ${shot?.label ? `<span>${readableImageLabel(shot)}</span>` : ""}
            </div>
          </button>
        `;
      }).join("");

      searchResults.querySelectorAll(".search-result").forEach((button) => {
        button.addEventListener("click", () => {
          const node = nodeById.get(button.dataset.nodeId);
          if (!node) return;
          searchDialog.close();
          clearSearch();
          openNodeModal(node);
        });
      });
    }

    function clearSearch() {
      state.filter = "";
      searchInput.value = "";
      applyFilter();
      renderSearchResults();
    }

    function openSearchDialog() {
      renderSearchResults();
      if (!searchDialog.open) searchDialog.showModal();
      window.setTimeout(() => searchInput.focus(), 0);
    }

    function closeSearchDialog(clear = true) {
      if (searchDialog.open) searchDialog.close();
      if (clear) clearSearch();
    }

    openSearchButton.addEventListener("click", () => openSearchDialog());
    closeSearchButton.addEventListener("click", () => closeSearchDialog(true));

    searchDialog.addEventListener("click", (event) => {
      const rect = searchDialog.getBoundingClientRect();
      const inside = rect.top <= event.clientY && event.clientY <= rect.top + rect.height && rect.left <= event.clientX && event.clientX <= rect.left + rect.width;
      if (!inside) closeSearchDialog(true);
    });

    searchInput.addEventListener("input", (event) => {
      state.filter = event.target.value.trim().toLowerCase();
      applyFilter();
      renderSearchResults();
    });

    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        const [first] = filteredNodes();
        if (!first) return;
        closeSearchDialog(true);
        openNodeModal(first);
      }
    });

    document.addEventListener("keydown", (event) => {
      const shortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
      if (shortcut) {
        event.preventDefault();
        if (searchDialog.open) closeSearchDialog(false);
        else openSearchDialog();
      }
      if (event.key === "Escape" && searchDialog.open) {
        closeSearchDialog(true);
      }
      if (event.key === "Escape" && !searchDialog.open && !modal.open && !dockPanel.hasAttribute("hidden")) {
        dockPanel.setAttribute("hidden", "");
        togglePanelButton.setAttribute("aria-expanded", "false");
      }
    });

    togglePanelButton.addEventListener("click", () => {
      const hidden = dockPanel.hasAttribute("hidden");
      if (hidden) {
        dockPanel.removeAttribute("hidden");
        togglePanelButton.setAttribute("aria-expanded", "true");
      } else {
        dockPanel.setAttribute("hidden", "");
        togglePanelButton.setAttribute("aria-expanded", "false");
      }
    });

    resetButton.addEventListener("click", () => {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(SCALE_STORAGE_KEY);
      state.positions = defaultPositions();
      state.scale = 1;
      state.nodeElements.forEach((element, nodeId) => {
        element.style.left = state.positions[nodeId].x + "px";
        element.style.top = state.positions[nodeId].y + "px";
      });
      ensureCanvasBounds();
      renderEdges();
    });

    let panState = null;
    frame.addEventListener("pointerdown", (event) => {
      if (event.target.closest(".node")) return;
      panState = {
        x: event.clientX,
        y: event.clientY,
        left: frame.scrollLeft,
        top: frame.scrollTop,
      };
      frame.setPointerCapture(event.pointerId);
    });
    frame.addEventListener("pointermove", (event) => {
      if (!panState) return;
      frame.scrollLeft = panState.left - (event.clientX - panState.x);
      frame.scrollTop = panState.top - (event.clientY - panState.y);
    });
    frame.addEventListener("pointerup", (event) => {
      if (!panState) return;
      panState = null;
      frame.releasePointerCapture(event.pointerId);
    });

    frame.addEventListener("wheel", (event) => {
      if (modal.open || searchDialog.open) return;
      event.preventDefault();
      const factor = Math.exp(-event.deltaY * 0.0012);
      const rect = frame.getBoundingClientRect();
      setScale(state.scale * factor, event.clientX - rect.left, event.clientY - rect.top);
    }, { passive: false });

    renderNodes();
    renderSearchResults();
    frame.scrollLeft = 0;
    frame.scrollTop = 0;
