    window.InteractionBoard.register("modal", (ctx) => {
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

      function renderModalGallery(node, galleryRefs, pendingRefs, activeIndex = 0) {
        const safeIndex = Math.min(Math.max(activeIndex, 0), Math.max(0, galleryRefs.length - 1));
        if (!galleryRefs.length) {
          ctx.elements.modalPreview.innerHTML = `
          <div class="empty-note preview-empty">
            暂无真实快照
            ${pendingRefs.length ? `<br /><code>已规划 ${pendingRefs.length} 个待补截图</code>` : ""}
          </div>
        `;
          ctx.elements.modalVersions.innerHTML = "";
          return;
        }

        const activeRef = galleryRefs[safeIndex];
        ctx.elements.modalPreview.innerHTML = `
        <figure class="preview-figure">
          <div class="preview-frame">
            <img src="${activeRef.relative_path || activeRef.path}" alt="${ctx.controllers.helpers.escapeHtml(node.title)} ${ctx.controllers.helpers.escapeHtml(activeRef.label || "")}" loading="lazy" />
          </div>
          <figcaption class="preview-caption">
            <div>
              <strong>${ctx.controllers.helpers.readableImageLabel(activeRef)}</strong>
              <span>${galleryRefs.length > 1 ? `版本 ${safeIndex + 1} / ${galleryRefs.length}` : "当前版本"}</span>
            </div>
            <code>${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.refDisplayPath(activeRef))}</code>
          </figcaption>
        </figure>
      `;

        ctx.elements.modalVersions.innerHTML = `
        <div class="version-rail-track">
          ${galleryRefs.map((ref, index) => `
            <button
              type="button"
              class="version-thumb ${index === safeIndex ? "active" : ""}"
              data-index="${index}"
            >
              <span class="version-thumb-media">
                <img src="${ref.relative_path || ref.path}" alt="${ctx.controllers.helpers.escapeHtml(node.title)} ${ctx.controllers.helpers.escapeHtml(ref.label || "")}" loading="lazy" />
              </span>
              <span class="version-thumb-meta">
                <strong>${ctx.controllers.helpers.readableImageLabel(ref)}</strong>
                <small>${index === 0 ? "主版本" : `版本 ${index + 1}`}</small>
              </span>
            </button>
          `).join("")}
        </div>
        ${pendingRefs.length ? `<div class="version-pending-note">另有 ${pendingRefs.length} 个待补截图已折叠，不在主预览区展示。</div>` : ""}
      `;

        ctx.elements.modalVersions.querySelectorAll(".version-thumb").forEach((button) => {
          button.addEventListener("click", () => {
            renderModalGallery(node, galleryRefs, pendingRefs, Number(button.dataset.index || 0));
          });
        });
      }

      function renderModalFlows(node, outgoing, incoming) {
        const sections = [
          { label: "后续页面", items: outgoing, direction: "out" },
          { label: "上游入口", items: incoming, direction: "in" },
        ].filter((section) => section.items.length);

        if (!sections.length) {
          ctx.elements.modalEdges.innerHTML = `<div class="empty-note compact">当前节点还没有登记流向。</div>`;
          return;
        }

        ctx.elements.modalEdges.innerHTML = sections.map((section) => `
        <section class="flow-group">
          <h4>${section.label}</h4>
          <div class="flow-group-list">
            ${section.items.map((edge) => {
              const targetId = section.direction === "out" ? edge.to : edge.from;
              const targetNode = ctx.graph.nodeById.get(targetId);
              const title = targetNode?.title || targetId;
              return `
                <button type="button" class="flow-item" data-target-node="${ctx.controllers.helpers.escapeHtml(targetId)}">
                  <span class="flow-direction">${section.direction === "out" ? "→" : "←"} ${ctx.controllers.helpers.escapeHtml(edge.kind || "link")}</span>
                  <strong>${ctx.controllers.helpers.escapeHtml(title)}</strong>
                  <code>${ctx.controllers.helpers.escapeHtml(edge.trigger || "n/a")}</code>
                </button>
              `;
            }).join("")}
          </div>
        </section>
      `).join("");

        ctx.elements.modalEdges.querySelectorAll(".flow-item[data-target-node]").forEach((button) => {
          button.addEventListener("click", () => {
            const targetNode = ctx.graph.nodeById.get(button.dataset.targetNode);
            if (!targetNode) return;
            openNodeModal(targetNode);
          });
        });
      }

      function renderModalAutomation(node, codeEntry, codeAnchors, scenarioRefs) {
        const pageFile = ctx.controllers.helpers.repoRelativePath(codeEntry.page_file || node.page_file || "");
        const screenComponent = codeEntry.screen_component || node.screen_component || "";
        const mainAnchor = codeAnchors[0];
        const visibleScenarios = scenarioRefs.slice(0, 4);
        ctx.elements.modalScenarios.innerHTML = `
        <article class="meta-card accent">
          <span class="meta-label">页面文件</span>
          <code>${ctx.controllers.helpers.escapeHtml(pageFile || "未解析")}</code>
        </article>
        <article class="meta-card">
          <span class="meta-label">组件</span>
          <code>${ctx.controllers.helpers.escapeHtml(screenComponent || "未解析")}</code>
        </article>
        ${mainAnchor ? `
          <article class="meta-card">
            <span class="meta-label">主锚点</span>
            <code>${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.repoRelativePath(mainAnchor.path || ""))}:${ctx.controllers.helpers.escapeHtml(mainAnchor.line || "")}</code>
          </article>
        ` : ""}
        <article class="meta-card">
          <span class="meta-label">自动化场景</span>
          ${visibleScenarios.length ? `
            <div class="meta-tags">
              ${visibleScenarios.map((ref) => `<span class="meta-tag">${ctx.controllers.helpers.escapeHtml(ref.scenario_id || "scenario")}</span>`).join("")}
            </div>
            ${scenarioRefs.length > visibleScenarios.length ? `<p class="meta-note">另有 ${scenarioRefs.length - visibleScenarios.length} 个场景已折叠。</p>` : ""}
          ` : `<p class="meta-note">当前没有自动化场景。</p>`}
        </article>
      `;
      }

      function openNodeModal(node) {
        ctx.controllers.store.ensureNodeVisible(node);
        const outgoing = ctx.data.edges.filter((edge) => edge.from === node.node_id);
        const incoming = ctx.data.edges.filter((edge) => edge.to === node.node_id);
        const codeEntry = node.card?.code_entry || {};
        const codeAnchors = node.card?.code_anchors?.length ? node.card.code_anchors : (node.source_refs || []);
        const scenarioRefs = node.card?.scenario_refs || [];
        const allRefs = ctx.controllers.helpers.uniqueImageRefs(node);
        const existingRefs = allRefs.filter((ref) => ref.exists);
        const pendingRefs = allRefs.filter((ref) => !ref.exists);
        const pageFile = ctx.controllers.helpers.repoRelativePath(codeEntry.page_file || node.page_file || "");
        const storyParts = [...new Set([node.board_meta?.note, ...(node.regions || [])].filter(Boolean))];

        ctx.elements.modalTitle.textContent = node.title;
        ctx.elements.modalSubtitle.innerHTML = `<code>${ctx.controllers.helpers.escapeHtml(node.route || "/")}</code>${pageFile ? `<span>${ctx.controllers.helpers.escapeHtml(pageFile)}</span>` : ""}`;
        ctx.elements.modalBadges.innerHTML = [
          `<span class="modal-badge">${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.formatStatus(node))}</span>`,
          `<span class="modal-badge subtle">${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.groupLabel(node.group))}</span>`,
          `<span class="modal-badge subtle">${existingRefs.length ? `${existingRefs.length} 个版本` : "暂无快照"}</span>`,
          `<span class="modal-badge subtle">${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.scenarioSummary(node))}</span>`,
        ].join("");
        ctx.elements.modalStory.hidden = !storyParts.length;
        ctx.elements.modalStory.textContent = storyParts.slice(0, 3).join(" · ");
        renderModalGallery(node, existingRefs, pendingRefs, 0);
        renderModalFlows(node, outgoing, incoming);
        renderModalAutomation(node, codeEntry, codeAnchors, scenarioRefs);

        fillList(ctx.elements.modalRegions, node.regions || [], (item) => ctx.controllers.helpers.escapeHtml(item));
        fillList(ctx.elements.modalRefs, codeAnchors, (ref) => `<code>${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.repoRelativePath(ref.path || ""))}:${ctx.controllers.helpers.escapeHtml(ref.line || "")}</code>`);
        fillList(ctx.elements.modalAssets, allRefs, (ref) => `<strong>${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.readableImageLabel(ref))}</strong><br /><code>${ctx.controllers.helpers.escapeHtml(ctx.controllers.helpers.refDisplayPath(ref))}</code>`);

        if (!ctx.elements.modal.open) ctx.elements.modal.showModal();
        ctx.controllers.viewport.centerNode(node.node_id);
        ctx.controllers.renderer.setHighlight(node.node_id);
      }

      function closeNodeModal() {
        ctx.elements.modal.close();
        ctx.controllers.renderer.setHighlight("");
      }

      function handleBackdropClick(event) {
        const rect = ctx.elements.modal.getBoundingClientRect();
        const inside = rect.top <= event.clientY && event.clientY <= rect.top + rect.height && rect.left <= event.clientX && event.clientX <= rect.left + rect.width;
        if (!inside) closeNodeModal();
      }

      return {
        openNodeModal,
        closeNodeModal,
        handleBackdropClick,
      };
    });
