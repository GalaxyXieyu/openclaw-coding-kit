    window.InteractionBoard.register("bindings", (ctx) => {
      let bound = false;

      function setDockPanelVisible(visible) {
        if (visible) {
          ctx.elements.dockPanel.removeAttribute("hidden");
          ctx.elements.togglePanelButton.setAttribute("aria-expanded", "true");
        } else {
          ctx.elements.dockPanel.setAttribute("hidden", "");
          ctx.elements.togglePanelButton.setAttribute("aria-expanded", "false");
        }
      }

      function handleGlobalKeydown(event) {
        const shortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
        if (shortcut) {
          event.preventDefault();
          if (ctx.elements.searchDialog.open) ctx.controllers.search.closeSearchDialog(false);
          else ctx.controllers.search.openSearchDialog();
        }
        if (event.key === "Escape" && ctx.elements.searchDialog.open) {
          ctx.controllers.search.closeSearchDialog(true);
        }
        if (event.key === "Escape" && !ctx.elements.searchDialog.open && !ctx.elements.modal.open && !ctx.elements.dockPanel.hasAttribute("hidden")) {
          setDockPanelVisible(false);
        }
      }

      function bindDomEvents() {
        if (bound) return;
        bound = true;

        ctx.elements.openSearchButton.addEventListener("click", () => ctx.controllers.search.openSearchDialog());
        ctx.elements.closeSearchButton.addEventListener("click", () => ctx.controllers.search.closeSearchDialog(true));
        ctx.elements.searchDialog.addEventListener("click", (event) => ctx.controllers.search.handleBackdropClick(event));
        ctx.elements.searchInput.addEventListener("input", (event) => ctx.controllers.search.handleInput(event));
        ctx.elements.searchInput.addEventListener("keydown", (event) => ctx.controllers.search.handleKeydown(event));

        ctx.elements.modalClose.addEventListener("click", () => ctx.controllers.modal.closeNodeModal());
        ctx.elements.modal.addEventListener("click", (event) => ctx.controllers.modal.handleBackdropClick(event));
        ctx.elements.modal.addEventListener("close", () => ctx.controllers.renderer.setHighlight(""));

        document.addEventListener("keydown", (event) => handleGlobalKeydown(event));

        ctx.elements.togglePanelButton.addEventListener("click", () => {
          setDockPanelVisible(ctx.elements.dockPanel.hasAttribute("hidden"));
        });

        ctx.elements.resetButton.addEventListener("click", () => {
          ctx.controllers.store.resetLayout();
          ctx.controllers.renderer.renderBoard({ preserveScroll: false });
        });

        ctx.controllers.viewport.bindPanAndZoom();
      }

      return { bindDomEvents };
    });
