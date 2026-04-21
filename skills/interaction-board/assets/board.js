    (() => {
      try {
        if (!window.InteractionBoard || typeof window.InteractionBoard.start !== "function") {
          throw new Error("InteractionBoard bootstrap is missing");
        }
        window.InteractionBoard.start();
      } catch (error) {
        console.error("InteractionBoard failed to start", error);
        throw error;
      }
    })();
