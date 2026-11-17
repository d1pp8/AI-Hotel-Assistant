// Minimal chat client: no framework, no build step. Talks to POST /chat and
// GET /conversations/{id}/messages.

const STORAGE_KEY = "hotel-chat-conversation-id";

const messagesEl = document.getElementById("messages");
const welcomeEl = document.getElementById("welcome");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const newChatBtn = document.getElementById("new-chat");

// localStorage can throw (private mode, blocked storage): the chat must still work without it.
function loadConversationId() {
  try { return localStorage.getItem(STORAGE_KEY); } catch { return null; }
}
function saveConversationId(id) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch { /* ignore */ }
}

let conversationId = loadConversationId();
let busy = false;

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// textContent (never innerHTML) for anything coming from the user or the LLM: prevents XSS.
function addMessage(role, text, sources) {
  welcomeEl.hidden = true;
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);

  if (sources && sources.length) {
    const details = document.createElement("details");
    details.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = `Quellen (${sources.length})`;
    details.appendChild(summary);
    const list = document.createElement("ul");
    for (const s of sources) {
      const li = document.createElement("li");
      li.textContent = `${s.title} `;
      const score = document.createElement("span");
      score.className = "score";
      score.textContent = `· ${s.score.toFixed(2)}`;
      li.appendChild(score);
      list.appendChild(li);
    }
    details.appendChild(list);
    wrap.appendChild(details);
  }

  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function showTyping() {
  const el = document.createElement("div");
  el.className = "msg assistant";
  el.innerHTML = '<div class="bubble typing"><span></span><span></span><span></span></div>';
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
}

async function send(text) {
  text = text.trim();
  if (!text || busy) return;

  addMessage("user", text);
  input.value = "";
  autoResize();
  setBusy(true);
  const typing = showTyping();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, conversation_id: conversationId }),
    });
    const data = await res.json().catch(() => ({}));

    if (res.status === 404) {
      // The stored conversation no longer exists (e.g. DB was reset): start fresh.
      conversationId = null;
      saveConversationId(null);
      throw new Error("Die Unterhaltung wurde nicht gefunden. Bitte senden Sie Ihre Frage erneut.");
    }
    if (!res.ok) {
      throw new Error(data.detail ? `Fehler: ${data.detail}` : `Fehler ${res.status}`);
    }

    conversationId = data.conversation_id;
    saveConversationId(conversationId);
    typing.remove();
    addMessage("assistant", data.answer, data.sources);
  } catch (err) {
    typing.remove();
    const msg = err instanceof TypeError ? "Server nicht erreichbar." : err.message;
    addMessage("assistant error", msg);
  } finally {
    setBusy(false);
    input.focus();
  }
}

async function restoreHistory() {
  if (!conversationId) return;
  try {
    const res = await fetch(`/conversations/${conversationId}/messages`);
    if (!res.ok) throw new Error();
    for (const m of await res.json()) addMessage(m.role, m.content);
  } catch {
    conversationId = null;
    saveConversationId(null);
  }
}

function newChat() {
  conversationId = null;
  saveConversationId(null);
  messagesEl.querySelectorAll(".msg").forEach((el) => el.remove());
  welcomeEl.hidden = false;
  input.focus();
}

function autoResize() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
  input.style.overflowY = input.scrollHeight > 160 ? "auto" : "hidden";
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  send(input.value);
});

// Enter sends, Shift+Enter makes a new line.
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send(input.value);
  }
});
input.addEventListener("input", autoResize);

document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => send(chip.textContent))
);
newChatBtn.addEventListener("click", newChat);

restoreHistory();
autoResize();
input.focus();
