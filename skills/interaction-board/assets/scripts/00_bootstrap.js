    window.InteractionBoard = (() => {
      const registry = new Map();
      const instances = new Map();
      let context = null;

      function register(name, factory) {
        registry.set(name, factory);
      }

      function use(name) {
        if (!context) throw new Error("InteractionBoard context is not ready");
        if (!instances.has(name)) {
          const factory = registry.get(name);
          if (!factory) throw new Error(`InteractionBoard module not registered: ${name}`);
          instances.set(name, factory(context));
        }
        return instances.get(name);
      }

      function metricVar(name, fallback) {
        const bodyStyle = window.getComputedStyle(document.body);
        const rootStyle = window.getComputedStyle(document.documentElement);
        const resolved = parseFloat(bodyStyle.getPropertyValue(name) || rootStyle.getPropertyValue(name));
        if (!Number.isFinite(resolved) || resolved <= 0) return fallback;
        return resolved;
      }

      function collectElements() {
        return {
          viewport: document.getElementById("boardViewport"),
          stage: document.getElementById("boardStage"),
          frame: document.getElementById("boardFrame"),
          edgeLayer: document.getElementById("edgeLayer"),
          tooltip: document.getElementById("boardTooltip"),
          modal: document.getElementById("nodeModal"),
          modalTitle: document.getElementById("modalTitle"),
          modalSubtitle: document.getElementById("modalSubtitle"),
          modalBadges: document.getElementById("modalBadges"),
          modalStory: document.getElementById("modalStory"),
          modalPreview: document.getElementById("modalPreview"),
          modalVersions: document.getElementById("modalVersions"),
          modalRegions: document.getElementById("modalRegions"),
          modalRefs: document.getElementById("modalRefs"),
          modalAssets: document.getElementById("modalAssets"),
          modalScenarios: document.getElementById("modalScenarios"),
          modalEdges: document.getElementById("modalEdges"),
          modalClose: document.getElementById("modalClose"),
          searchDialog: document.getElementById("searchDialog"),
          searchInput: document.getElementById("boardSearch"),
          searchResults: document.getElementById("searchResults"),
          openSearchButton: document.getElementById("openSearch"),
          closeSearchButton: document.getElementById("closeSearch"),
          togglePanelButton: document.getElementById("togglePanel"),
          resetButton: document.getElementById("resetLayout"),
          dockPanel: document.getElementById("dockPanel"),
        };
      }

      function buildGraph(data, groupOrder) {
        const grouped = {};
        const nodeById = new Map();
        data.nodes.forEach((node) => {
          grouped[node.group] = grouped[node.group] || [];
          grouped[node.group].push(node);
          nodeById.set(node.node_id, node);
        });
        const orderedGroups = Object.keys(grouped).sort((a, b) => (groupOrder[a] ?? 99) - (groupOrder[b] ?? 99) || a.localeCompare(b));
        return { grouped, nodeById, orderedGroups };
      }

      function createContext() {
        const data = JSON.parse(document.getElementById("board-data").textContent);
        const groupOrder = __GROUP_ORDER__;
        const groupLabels = {
          entry: "入口",
          admin: "管理后台",
          guiquan: "龟圈",
          products: "宠物",
          footprint: "足迹",
          account: "账号",
          public: "公开",
          candidate: "候选",
          other: "其他",
        };
        const boardKind = String(data.project?.app_kind || "").trim();
        if (boardKind) {
          document.body.dataset.boardKind = boardKind;
        }
        if (data.nodes.length > 28 || data.edges.length > 42) {
          document.body.dataset.density = "high";
        }

        const layeredCanvasEnabled = boardKind.startsWith("web") || data.nodes.length > 18;
        const storageKey = "interaction-board-layout::" + (data.project?.name || "board") + "::v6";
        return {
          data,
          elements: collectElements(),
          graph: buildGraph(data, groupOrder),
          constants: {
            groupOrder,
            groupLabels,
            boardKind,
            layeredCanvasEnabled,
            defaultVisibleLevel: layeredCanvasEnabled ? 2 : Number.POSITIVE_INFINITY,
            storageKey,
            scaleStorageKey: storageKey + "::scale",
          },
          metrics: {
            nodeWidth: metricVar("--node-width", 188),
            nodeHeight: metricVar("--node-height", 346),
            laneMinGap: metricVar("--lane-min-gap", 228),
            laneWidth: metricVar("--lane-width", 196),
            lanePaddingTop: metricVar("--lane-padding-top", 94),
            nodeGapY: metricVar("--node-gap-y", 344),
            minScale: 0.72,
            maxScale: 1.6,
          },
          controllers: {},
          use,
        };
      }

      function start() {
        if (context) return context;
        instances.clear();
        context = createContext();
        const helpers = use("helpers");
        const viewport = use("viewport");
        const store = use("store");
        context.state = store.createInitialState();
        const renderer = use("render");
        const modal = use("modal");
        const search = use("search");
        const interactions = use("interactions");
        const bindings = use("bindings");
        context.controllers = { helpers, viewport, store, renderer, modal, search, interactions, bindings };
        bindings.bindDomEvents();
        renderer.renderBoard({ preserveScroll: false });
        context.elements.frame.scrollLeft = 0;
        context.elements.frame.scrollTop = 0;
        return context;
      }

      return { register, start };
    })();
