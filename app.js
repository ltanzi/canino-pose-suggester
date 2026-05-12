(() => {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  // Per-size state:
  //   history  — ordered list of pose ids shown
  //   cursor   — index in history of currently-shown pose (-1 if none yet)
  //   unseen   — Set of pose ids not yet shown this cycle; refills when empty
  const state = {
    groupSize: 1,
    library: {},
    loading: {},
    historyBySize: {},
    cursorBySize: {},
    unseenBySize: {},
  };

  const canvas = document.getElementById("canvas");
  const figuresLayer = document.getElementById("figures");
  const poseLabel = document.getElementById("pose-label");
  const pills = Array.from(document.querySelectorAll(".pill"));
  const generateBtn = document.getElementById("generate");
  const backBtn = document.getElementById("back");

  function setActiveSize(size) {
    state.groupSize = size;
    for (const pill of pills) {
      pill.setAttribute(
        "aria-pressed",
        Number(pill.dataset.size) === size ? "true" : "false"
      );
    }
    updateNavButtons();
  }

  async function loadLibrary(groupSize) {
    if (state.library[groupSize]) return state.library[groupSize];
    if (state.loading[groupSize]) return state.loading[groupSize];

    const url = `./poses/${groupSize}.json`;
    state.loading[groupSize] = fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
        return res.json();
      })
      .then((poses) => {
        for (const pose of poses) {
          if (!pose.figures || pose.figures.length !== groupSize) {
            console.warn(
              `Pose "${pose.id}" has ${pose.figures?.length ?? 0} figures, expected ${groupSize}`
            );
          }
        }
        state.library[groupSize] = poses;
        delete state.loading[groupSize];
        return poses;
      });

    return state.loading[groupSize];
  }

  function renderPose(pose) {
    while (figuresLayer.firstChild) figuresLayer.removeChild(figuresLayer.firstChild);

    for (const figure of pose.figures) {
      if (figure.head) {
        const { cx, cy, r } = figure.head;
        const circle = document.createElementNS(SVG_NS, "circle");
        circle.setAttribute("cx", cx);
        circle.setAttribute("cy", cy);
        circle.setAttribute("r", r);
        figuresLayer.appendChild(circle);
      }
      for (const ln of figure.lines || []) {
        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("x1", ln.x1);
        line.setAttribute("y1", ln.y1);
        line.setAttribute("x2", ln.x2);
        line.setAttribute("y2", ln.y2);
        figuresLayer.appendChild(line);
      }
    }

    canvas.classList.add("is-rendered");
    canvas.setAttribute("aria-label", `Pose: ${pose.name}`);
    if (poseLabel) {
      poseLabel.textContent = pose.name;
    }
  }

  function ensureSizeState(size, library) {
    if (!state.historyBySize[size]) state.historyBySize[size] = [];
    if (state.cursorBySize[size] == null) state.cursorBySize[size] = -1;
    if (!state.unseenBySize[size]) {
      state.unseenBySize[size] = new Set(library.map((p) => p.id));
    }
  }

  async function generate() {
    const size = state.groupSize;
    const library = await loadLibrary(size);
    ensureSizeState(size, library);

    const history = state.historyBySize[size];
    const cursor = state.cursorBySize[size];

    // If we've gone Back, Generate first walks forward through history before
    // picking a new pose — like a browser's Forward button.
    if (cursor < history.length - 1) {
      const nextCursor = cursor + 1;
      state.cursorBySize[size] = nextCursor;
      const pose = library.find((p) => p.id === history[nextCursor]);
      if (pose) renderPose(pose);
      updateNavButtons();
      return;
    }

    let unseen = state.unseenBySize[size];
    if (unseen.size === 0) {
      // All poses shown this cycle — refill, dropping the just-shown pose so
      // it doesn't immediately repeat at the cycle boundary.
      const current = history[cursor];
      unseen = new Set(library.map((p) => p.id));
      if (current && unseen.size > 1) unseen.delete(current);
      state.unseenBySize[size] = unseen;
    }

    const ids = Array.from(unseen);
    const chosen = ids[Math.floor(Math.random() * ids.length)];
    unseen.delete(chosen);

    history.push(chosen);
    state.cursorBySize[size] = history.length - 1;

    const pose = library.find((p) => p.id === chosen);
    if (pose) renderPose(pose);
    updateNavButtons();
  }

  async function goBack() {
    const size = state.groupSize;
    const cursor = state.cursorBySize[size];
    if (cursor == null || cursor <= 0) return;
    const library = await loadLibrary(size);
    const prevId = state.historyBySize[size][cursor - 1];
    state.cursorBySize[size] = cursor - 1;
    const pose = library.find((p) => p.id === prevId);
    if (pose) renderPose(pose);
    updateNavButtons();
  }

  function updateNavButtons() {
    const cursor = state.cursorBySize[state.groupSize];
    backBtn.disabled = !(cursor != null && cursor > 0);
  }

  for (const pill of pills) {
    pill.addEventListener("click", () => {
      const size = Number(pill.dataset.size);
      if (size === state.groupSize) return;
      setActiveSize(size);
    });
  }

  generateBtn.addEventListener("click", generate);
  backBtn.addEventListener("click", goBack);

  setActiveSize(1);
})();
