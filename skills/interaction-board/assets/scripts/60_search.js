    window.InteractionBoard.register("search", (ctx) => {
      function renderSearchResults() {
        const matches = ctx.controllers.store.filteredNodes().slice(0, 18);
        if (!matches.length) {
          ctx.elements.searchResults.innerHTML = `<div class="search-empty">${ctx.state.filter ? "没有命中节点，试试路由、组件名或截图来源标签。" : "输入关键词后会显示匹配节点。"} </div>`;
          return;
        }
        ctx.elements.searchResults.innerHTML = matches.map((node) => {
          const shot = ctx.controllers.helpers.primaryShot(node);
          const stats = ctx.controllers.helpers.scenarioStats(node);
          const versions = ctx.controllers.helpers.displayRefs(node).filter((item) => item.exists).length;
          return `
          <button type="button" class="search-result" data-node-id="${node.node_id}">
            <strong>${node.title}</strong>
            <code>${node.route}</code>
            <div class="search-result-meta">
              <span>${ctx.controllers.helpers.formatStatus(node)}</span>
              <span>${ctx.controllers.helpers.groupLabel(node.group)}</span>
              <span>${versions ? `${versions} 个版本` : "无快照"}</span>
              <span>${stats.visible_count ? `${stats.visible_count} 个主场景` : "无场景"}</span>
              ${shot?.label ? `<span>${ctx.controllers.helpers.readableImageLabel(shot)}</span>` : ""}
            </div>
          </button>
        `;
        }).join("");

        ctx.elements.searchResults.querySelectorAll(".search-result").forEach((button) => {
          button.addEventListener("click", () => {
            const node = ctx.graph.nodeById.get(button.dataset.nodeId);
            if (!node) return;
            ctx.elements.searchDialog.close();
            clearSearch();
            ctx.controllers.modal.openNodeModal(node);
          });
        });
      }

      function clearSearch() {
        ctx.state.filter = "";
        ctx.elements.searchInput.value = "";
        ctx.controllers.renderer.applyFilter();
        renderSearchResults();
      }

      function openSearchDialog() {
        renderSearchResults();
        if (!ctx.elements.searchDialog.open) ctx.elements.searchDialog.showModal();
        window.setTimeout(() => ctx.elements.searchInput.focus(), 0);
      }

      function closeSearchDialog(clear = true) {
        if (ctx.elements.searchDialog.open) ctx.elements.searchDialog.close();
        if (clear) clearSearch();
      }

      function handleBackdropClick(event) {
        const rect = ctx.elements.searchDialog.getBoundingClientRect();
        const inside = rect.top <= event.clientY && event.clientY <= rect.top + rect.height && rect.left <= event.clientX && event.clientX <= rect.left + rect.width;
        if (!inside) closeSearchDialog(true);
      }

      function handleInput(event) {
        ctx.state.filter = event.target.value.trim().toLowerCase();
        ctx.controllers.renderer.applyFilter();
        renderSearchResults();
      }

      function handleKeydown(event) {
        if (event.key !== "Enter") return;
        event.preventDefault();
        const [first] = ctx.controllers.store.filteredNodes();
        if (!first) return;
        closeSearchDialog(true);
        ctx.controllers.modal.openNodeModal(first);
      }

      return {
        renderSearchResults,
        clearSearch,
        openSearchDialog,
        closeSearchDialog,
        handleBackdropClick,
        handleInput,
        handleKeydown,
      };
    });
