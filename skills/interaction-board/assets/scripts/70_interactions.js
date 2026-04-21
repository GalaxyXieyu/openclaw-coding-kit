    window.InteractionBoard.register("interactions", (ctx) => {
      function startDrag(event, node, element) {
        if (event.button !== 0) return;
        event.preventDefault();
        const origin = ctx.state.positions[node.node_id];
        ctx.state.dragging = {
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
        ctx.controllers.renderer.setHighlight(node.node_id);

        const handleMove = (moveEvent) => {
          if (!ctx.state.dragging || ctx.state.dragging.pointerId !== moveEvent.pointerId) return;
          const dx = moveEvent.clientX - ctx.state.dragging.startX;
          const dy = moveEvent.clientY - ctx.state.dragging.startY;
          if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
            element.dataset.dragMoved = "true";
          }
          ctx.state.positions[node.node_id] = {
            x: Math.max(18, ctx.state.dragging.originX + dx),
            y: Math.max(18, ctx.state.dragging.originY + dy),
          };
          element.style.left = ctx.state.positions[node.node_id].x + "px";
          element.style.top = ctx.state.positions[node.node_id].y + "px";
          ctx.controllers.viewport.ensureCanvasBounds();
          ctx.controllers.renderer.renderEdges();
        };

        const handleUp = (upEvent) => {
          if (!ctx.state.dragging || ctx.state.dragging.pointerId !== upEvent.pointerId) return;
          element.classList.remove("dragging");
          element.releasePointerCapture(upEvent.pointerId);
          ctx.state.dragging = null;
          ctx.controllers.store.savePositions();
          ctx.controllers.renderer.renderEdges();
          window.removeEventListener("pointermove", handleMove);
          window.removeEventListener("pointerup", handleUp);
        };

        window.addEventListener("pointermove", handleMove);
        window.addEventListener("pointerup", handleUp);
      }

      return { startDrag };
    });
