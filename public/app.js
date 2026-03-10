let gameState = null;
let uiHints = null;
const SAVE_KEY = "wms_web_save_v1";

const setup = document.getElementById("setup");
const game = document.getElementById("game");
const scenarioEl = document.getElementById("scenario");
const heroEl = document.getElementById("hero");
const statusEl = document.getElementById("status");
const actionButtons = document.getElementById("actionButtons");
const messagesEl = document.getElementById("messages");
const aiLogsEl = document.getElementById("aiLogs");
const moveWrap = document.getElementById("moveWrap");
const destinationEl = document.getElementById("destination");
const moveBtn = document.getElementById("moveBtn");
const rallyWrap = document.getElementById("rallyWrap");
const candidateEl = document.getElementById("candidate");
const rallyBtn = document.getElementById("rallyBtn");
const mapInfoEl = document.getElementById("mapInfo");
const saveBtn = document.getElementById("saveBtn");
const loadBtn = document.getElementById("loadBtn");
const clearSaveBtn = document.getElementById("clearSaveBtn");

const ACTION_LABELS = {
    move: "이동",
    investigate: "조사",
    recruit: "모병",
    admin: "내정",
    class_action: "특기",
    rally: "집결",
    siege: "공성",
    rest: "휴식",
    end: "턴 종료"
};

async function api(path, method = "GET", body = null) {
    const res = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : null
    });
    return await res.json();
}

function cleanText(line) {
    if (!line) return "";
    return String(line)
        .replace(/\[[^\]]*\]/g, "")
        .replace(/\s+/g, " ")
        .trim();
}

function playerHero() {
    if (!gameState) return null;
    return Object.values(gameState.heroes).find(h => h.is_player_controlled);
}

function townName(id) {
    const t = gameState.towns[id];
    return t ? t.name_ko : id;
}

function renderStatus() {
    const hero = playerHero();
    if (!hero) return;
    const town = gameState.towns[hero.current_town];
    const faction = gameState.factions[hero.faction_id];
    statusEl.innerHTML = `
    <h2>턴 ${gameState.turn} / 남은 턴 ${Math.max(0, gameState.max_turns - gameState.turn)}</h2>
    <p><strong>${hero.name_ko}</strong> (${hero.hero_class})</p>
    <p>위치: ${town?.name_ko || hero.current_town} | AP: ${hero.action_points} | HP: ${hero.hp}/${hero.max_hp} | 병력: ${hero.current_army}</p>
    <p>세력: ${faction?.name_ko || hero.faction_id} | 금전: ${faction?.gold ?? hero.personal_gold} | 군량: ${faction?.food ?? "-"} | 안정도: ${gameState.dynasty_stability}</p>
  `;
}

function renderMap() {
    const hero = playerHero();
    if (!hero || !mapInfoEl) return;
    const town = gameState.towns[hero.current_town];
    if (!town) return;

    const neighbors = (town.adjacent || []).map(id => gameState.towns[id]).filter(Boolean);
    const allies = Object.values(gameState.heroes).filter(h => h.current_town === hero.current_town && h.id !== hero.id);

    const neighborPills = neighbors.length
        ? neighbors.map(t => `<span class="pill">${t.name_ko}</span>`).join("")
        : "인접 도시 없음";
    const allyText = allies.length
        ? allies.slice(0, 8).map(h => `${h.name_ko}(${h.faction_id})`).join(", ")
        : "같은 지역 장수 없음";

    mapInfoEl.innerHTML = [
        `<p><strong>현재:</strong> ${town.name_ko} (${town.id})</p>`,
        `<p><strong>인접 지역</strong></p><div>${neighborPills}</div>`,
        `<p><strong>동일 지역 장수</strong></p><p>${allyText}</p>`
    ].join("");
}

function addLog(target, lines) {
    if (!lines || !lines.length) return;
    const text = lines.map(x => `- ${cleanText(x)}`).join("\n");
    target.textContent = `${text}\n${target.textContent}`.trim();
}

function renderActions() {
    actionButtons.innerHTML = "";
    moveWrap.hidden = true;
    rallyWrap.hidden = true;
    if (!uiHints) return;

    for (const action of uiHints.actions || []) {
        const btn = document.createElement("button");
        btn.textContent = ACTION_LABELS[action] || action;
        btn.onclick = () => runAction(action);
        actionButtons.appendChild(btn);
    }
}

function renderSelectors() {
    destinationEl.innerHTML = "";
    (uiHints?.destinations || []).forEach(d => {
        const o = document.createElement("option");
        o.value = d.id;
        o.textContent = `${d.name_ko} (${d.id})`;
        destinationEl.appendChild(o);
    });

    candidateEl.innerHTML = "";
    (uiHints?.contact_candidates || []).forEach(c => {
        const o = document.createElement("option");
        o.value = c.id;
        o.textContent = `${c.name_ko} [${c.hero_class}] 병력:${c.army}`;
        candidateEl.appendChild(o);
    });
}

async function runAction(action) {
    if (!gameState) return;
    if (action === "move") {
        moveWrap.hidden = false;
        return;
    }
    if (action === "rally") {
        rallyWrap.hidden = false;
        return;
    }
    const payload = { state: gameState, action };
    const r = await api("/api/game/action", "POST", payload);
    applyResponse(r);
}

async function runMove() {
    const r = await api("/api/game/action", "POST", {
        state: gameState,
        action: "move",
        destination_id: destinationEl.value || null
    });
    moveWrap.hidden = true;
    applyResponse(r);
}

async function runRally() {
    const r = await api("/api/game/action", "POST", {
        state: gameState,
        action: "rally",
        candidate_id: candidateEl.value || null
    });
    rallyWrap.hidden = true;
    applyResponse(r);
}

function applyResponse(r) {
    if (r.error) {
        addLog(messagesEl, [`오류: ${r.error}`]);
        return;
    }
    gameState = r.state;
    uiHints = r.ui_hints;
    renderStatus();
    renderMap();
    renderSelectors();
    renderActions();
    addLog(messagesEl, r.messages || []);
    addLog(aiLogsEl, r.ai_logs || []);
}

function saveSession() {
    if (!gameState) {
        addLog(messagesEl, ["저장할 게임 상태가 없습니다."]);
        return;
    }
    localStorage.setItem(SAVE_KEY, JSON.stringify({ state: gameState, ui_hints: uiHints }));
    addLog(messagesEl, ["세션 저장 완료"]);
}

function loadSession() {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) {
        addLog(messagesEl, ["저장된 세션이 없습니다."]);
        return;
    }
    try {
        const parsed = JSON.parse(raw);
        if (!parsed.state) throw new Error("invalid save");
        gameState = parsed.state;
        uiHints = parsed.ui_hints || {};
        setup.hidden = true;
        game.hidden = false;
        renderStatus();
        renderMap();
        renderSelectors();
        renderActions();
        addLog(messagesEl, ["저장된 세션 불러오기 완료"]);
    } catch (_e) {
        addLog(messagesEl, ["세션 불러오기 실패: 저장 데이터 손상"]);
    }
}

function clearSession() {
    localStorage.removeItem(SAVE_KEY);
    addLog(messagesEl, ["저장 세션 삭제 완료"]);
}

async function loadMeta() {
    const data = await api("/api/game/meta");
    scenarioEl.innerHTML = "";
    heroEl.innerHTML = "";

    data.scenarios.forEach(s => {
        const o = document.createElement("option");
        o.value = s.id;
        o.textContent = `[${s.year}] ${s.name_ko}`;
        scenarioEl.appendChild(o);
    });

    data.heroes.forEach(h => {
        const o = document.createElement("option");
        o.value = h.id;
        o.textContent = `${h.name_ko} (${h.hero_class})`;
        heroEl.appendChild(o);
    });
}

document.getElementById("startBtn").onclick = async () => {
    const r = await api("/api/game/new", "POST", {
        scenario_id: scenarioEl.value,
        hero_id: heroEl.value
    });
    applyResponse(r);
    setup.hidden = true;
    game.hidden = false;
    saveSession();
};

moveBtn.onclick = runMove;
rallyBtn.onclick = runRally;
saveBtn.onclick = saveSession;
loadBtn.onclick = loadSession;
clearSaveBtn.onclick = clearSession;

if (localStorage.getItem(SAVE_KEY)) {
    addLog(messagesEl, ["저장된 세션이 있습니다. [불러오기]를 눌러 이어서 플레이하세요."]);
}

loadMeta();
