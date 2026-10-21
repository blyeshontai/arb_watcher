const CHECK_EVERY_MS = 1500;  // same pace as main.py

// ---------- small helpers ----------

function money(amount) {
  return "$" + Math.abs(amount).toFixed(2);
}

function percent(price) {
  // 0.38 -> "38%", 0.995 -> "99.5%"
  return Math.round(price * 1000) / 10 + "%";
}

function outcome(result) {
  // same wording as outcome() in hedge.py
  if (Math.abs(result) < 0.005) return "break even";
  if (result > 0) return "profit " + money(result);
  return "loss " + money(result);
}

function localTime(isoTime) {
  return new Date(isoTime).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

async function getJSON(url) {
  // ask our Python server for data; throw if it sent back an error
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}

// ---------- the loop ----------
// Each start gets a new id. A check that finishes after Stop sees the id
// changed and doesn't schedule another one. setTimeout (not setInterval)
// waits for each check to finish, so slow requests never pile up.

let loopId = 0;

function startLoop(check) {
  const myId = ++loopId;
  async function tick() {
    await check();
    if (myId === loopId) setTimeout(tick, CHECK_EVERY_MS);
  }
  tick();
}

function stopLoop() {
  loopId++;
}

// ---------- scan mode ----------

const scanStatus = document.getElementById("scan-status");
const pairsBox = document.getElementById("pairs");

async function checkScan() {
  try {
    const data = await getJSON("/status");
    if (data.message) {
      scanStatus.textContent = data.message;
      pairsBox.innerHTML = "";
      return;
    }

    let status = `Window closes ${localTime(data.close_time)} · updated ${new Date().toLocaleTimeString()}`;
    if (data.target_gap > 0) status += ` · target gap ${data.target_gap.toFixed(2)}`;
    scanStatus.textContent = status;

    pairsBox.innerHTML = "";
    for (const pair of data.pairs) {
      const card = document.createElement("div");
      card.className = pair.opportunity ? "card good" : "card";
      card.innerHTML = `
        <h2>${pair.label}${pair.opportunity ? " · OPPORTUNITY" : ""}</h2>
        <div>${(pair.price_sum * 100).toFixed(1)}¢ per pair before fees</div>
        <div class="profit ${pair.profit < 0 ? "loss" : ""}">${outcome(pair.profit)}</div>
        <div class="status">for ${data.shares} pairs, fees included</div>`;
      pairsBox.appendChild(card);
    }
  } catch (error) {
    scanStatus.textContent = error.message;
  }
}

// ---------- hedge mode ----------

const form = document.getElementById("leg-form");
const appInput = document.getElementById("app");
const sideInput = document.getElementById("side");
const priceInput = document.getElementById("price");
const costInput = document.getElementById("cost");
const sharesInput = document.getElementById("shares");
const plan = document.getElementById("plan");
const live = document.getElementById("live");
const hedgeStatus = document.getElementById("hedge-status");

function legQuery() {
  // the leg as URL params, like app=poly&side=up&price=38
  return new URLSearchParams({
    app: appInput.value,
    side: sideInput.value,
    price: priceInput.value,
  });
}

async function fillShares() {
  // once price and cost are typed, ask the server how many shares that bought
  if (!priceInput.value || !costInput.value) return;
  const query = legQuery();
  query.set("cost", costInput.value);
  try {
    const data = await getJSON("/shares?" + query);
    sharesInput.value = data.shares;
  } catch (error) {
    hedgeStatus.textContent = error.message;
  }
}

appInput.addEventListener("change", fillShares);
priceInput.addEventListener("change", fillShares);
costInput.addEventListener("change", fillShares);

let hedgeWindow = null;  // close time of the window my leg is in

async function checkHedge() {
  const query = legQuery();
  query.set("shares", sharesInput.value);
  try {
    const data = await getJSON("/hedge?" + query);

    document.getElementById("plan-paid").textContent =
      `You paid ${money(data.leg_cost)} for ${data.leg_label} at ${percent(Number(priceInput.value) / 100)}.`;
    document.getElementById("plan-hedge").textContent = `To hedge, buy ${data.hedge_label}.`;
    document.getElementById("plan-break-even").textContent = data.break_even === null
      ? "No break even. Hedging can only cut your loss."
      : `Your break even is ${percent(data.break_even)}.`;

    if (data.live === null) {
      live.className = "live";
      live.textContent = "No live price right now";
      return;
    }

    // the first price tells us which window the leg is in; stop when it ends
    if (hedgeWindow === null) hedgeWindow = data.live.close_time;
    if (data.live.close_time !== hedgeWindow) {
      stopLoop();
      live.className = "live";
      live.textContent = "This window is over";
      return;
    }

    const good = data.live.result >= 0;
    live.className = good ? "live good" : "live";
    live.textContent = `${good ? "HEDGE NOW · " : ""}${data.hedge_label} ${percent(data.live.price)}` +
      ` · enter ${money(data.live.enter)} · ${outcome(data.live.result)}`;
    hedgeStatus.textContent = "Updated " + new Date().toLocaleTimeString();
  } catch (error) {
    hedgeStatus.textContent = error.message;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();  // stop the browser reloading the page
  hedgeWindow = null;
  form.hidden = true;
  plan.hidden = false;
  live.className = "live";
  live.textContent = "Waiting for a price…";
  startLoop(checkHedge);
});

document.getElementById("stop").addEventListener("click", () => {
  stopLoop();
  plan.hidden = true;
  form.hidden = false;
  hedgeStatus.textContent = "";
});

// ---------- tabs ----------

const scanTab = document.getElementById("scan-tab");
const hedgeTab = document.getElementById("hedge-tab");

function showScan() {
  scanTab.classList.add("active");
  hedgeTab.classList.remove("active");
  document.getElementById("scan-view").hidden = false;
  document.getElementById("hedge-view").hidden = true;
  startLoop(checkScan);
}

function showHedge() {
  hedgeTab.classList.add("active");
  scanTab.classList.remove("active");
  document.getElementById("scan-view").hidden = true;
  document.getElementById("hedge-view").hidden = false;
  stopLoop();  // scanning pauses while hedging
  plan.hidden = true;
  form.hidden = false;
}

scanTab.addEventListener("click", showScan);
hedgeTab.addEventListener("click", showHedge);

showScan();
