/**
 * chatbot.js — Onekey AI Chatbot Widget
 * Drop-in script: adds a floating chat button bottom-right on any page.
 * Communicates with POST /chat (backend RAG endpoint).
 */
(function () {
  /* ── Inject <style> ────────────────────────────────────────────────── */
  const style = document.createElement("style");
  style.textContent = `
    /* Widget root */
    #ok-chat-widget {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Floating button */
    #ok-chat-btn {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: #000000;
      border: 3px solid #000000;
      box-shadow: 4px 4px 0px #555555;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.15s, box-shadow 0.15s;
      color: #ffffff;
      font-size: 1.6rem;
      outline: none;
    }
    #ok-chat-btn:hover {
      transform: translate(2px, 2px);
      box-shadow: 2px 2px 0px #555555;
    }
    #ok-chat-btn:active {
      transform: translate(4px, 4px);
      box-shadow: 0px 0px 0px #555555;
    }
    #ok-chat-btn .ok-btn-icon { display: block; transition: opacity 0.2s, transform 0.2s; }
    #ok-chat-btn .ok-btn-close { display: none; font-size: 1.3rem; }
    #ok-chat-btn.open .ok-btn-icon { display: none; }
    #ok-chat-btn.open .ok-btn-close { display: block; }

    /* Pulse ring */
    #ok-chat-btn::before {
      content: '';
      position: absolute;
      width: 72px;
      height: 72px;
      border-radius: 50%;
      background: rgba(0,0,0,0.1);
      animation: ok-pulse 2.5s infinite;
    }
    @keyframes ok-pulse {
      0%   { transform: scale(0.9); opacity: 0.7; }
      70%  { transform: scale(1.3); opacity: 0; }
      100% { transform: scale(0.9); opacity: 0; }
    }

    /* Tooltip */
    #ok-chat-tooltip {
      position: absolute;
      bottom: 70px;
      right: 0;
      background: #000;
      color: #fff;
      padding: 0.4rem 0.8rem;
      border-radius: 8px;
      border: 2px solid #000;
      box-shadow: 3px 3px 0 #555;
      font-size: 0.78rem;
      font-weight: 600;
      white-space: nowrap;
      opacity: 0;
      pointer-events: none;
      transform: translateY(6px);
      transition: opacity 0.2s, transform 0.2s;
    }
    #ok-chat-widget:hover #ok-chat-tooltip { opacity: 1; transform: translateY(0); }
    #ok-chat-widget.chat-open #ok-chat-tooltip { opacity: 0; }

    /* Chat window */
    #ok-chat-window {
      position: absolute;
      bottom: 76px;
      right: 0;
      width: 360px;
      max-height: 540px;
      background: #ffffff;
      border: 4px solid #000000;
      border-radius: 16px;
      box-shadow: 8px 8px 0px #000000;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
      transform: translateY(16px) scale(0.97);
      transition: opacity 0.25s, transform 0.25s;
    }
    #ok-chat-window.visible {
      opacity: 1;
      pointer-events: all;
      transform: translateY(0) scale(1);
    }

    /* Header */
    #ok-chat-header {
      background: #000000;
      color: #ffffff;
      padding: 1rem 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-shrink: 0;
    }
    #ok-chat-header .ok-avatar {
      width: 36px; height: 36px;
      border-radius: 50%;
      object-fit: cover;
      flex-shrink: 0;
    }
    #ok-chat-header .ok-title { font-size: 1rem; font-weight: 700; }
    #ok-chat-header .ok-subtitle { font-size: 0.75rem; opacity: 0.7; }
    .ok-status-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #22c55e; display: inline-block;
      margin-right: 4px; animation: ok-blink 1.5s infinite;
    }
    @keyframes ok-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

    /* Messages */
    #ok-chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      scroll-behavior: smooth;
    }
    #ok-chat-messages::-webkit-scrollbar { width: 4px; }
    #ok-chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }

    .ok-msg {
      max-width: 85%;
      padding: 0.65rem 0.9rem;
      border-radius: 12px;
      font-size: 0.9rem;
      line-height: 1.5;
      border: 2px solid #000000;
      word-break: break-word;
      animation: ok-pop 0.2s ease;
    }
    @keyframes ok-pop {
      from { transform: scale(0.95); opacity: 0; }
      to   { transform: scale(1);    opacity: 1; }
    }
    .ok-msg-user {
      align-self: flex-end;
      background: #000000;
      color: #ffffff;
      border-radius: 12px 12px 2px 12px;
    }
    .ok-msg-bot {
      align-self: flex-start;
      background: #f9fafb;
      color: #111827;
      border-radius: 12px 12px 12px 2px;
    }
    .ok-msg-bot.ok-thinking {
      opacity: 0.6;
      font-style: italic;
    }

    /* Typing dots */
    .ok-dots span {
      display: inline-block;
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #6b7280;
      margin: 0 2px;
      animation: ok-bounce 1.2s infinite;
    }
    .ok-dots span:nth-child(2) { animation-delay: 0.2s; }
    .ok-dots span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes ok-bounce {
      0%, 80%, 100% { transform: translateY(0); }
      40%            { transform: translateY(-6px); }
    }

    /* Footer / input area */
    #ok-chat-footer {
      border-top: 3px solid #000000;
      padding: 0.75rem 1rem;
      display: flex;
      gap: 0.5rem;
      align-items: flex-end;
      flex-shrink: 0;
      background: #ffffff;
    }
    #ok-chat-input {
      flex: 1;
      resize: none;
      border: 3px solid #000000;
      border-radius: 8px;
      padding: 0.6rem 0.8rem;
      font-size: 0.9rem;
      font-family: inherit;
      outline: none;
      max-height: 100px;
      overflow-y: auto;
      transition: box-shadow 0.15s;
      line-height: 1.4;
    }
    #ok-chat-input:focus {
      box-shadow: 3px 3px 0 #000000;
    }
    #ok-chat-input::placeholder { color: #9ca3af; }
    #ok-chat-send {
      width: 42px; height: 42px;
      background: #000000;
      color: #ffffff;
      border: 3px solid #000000;
      border-radius: 8px;
      font-size: 1.2rem;
      cursor: pointer;
      box-shadow: 3px 3px 0 #555555;
      transition: transform 0.15s, box-shadow 0.15s;
      flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      padding: 0;
      line-height: 1;
    }
    #ok-chat-send:hover { transform: translate(1px,1px); box-shadow: 2px 2px 0 #555; }
    #ok-chat-send:active { transform: translate(3px,3px); box-shadow: 0 0 0 #555; }
    #ok-chat-send:disabled { background: #9ca3af; cursor: not-allowed; transform: none; }

    /* Branding footer */
    .ok-powered {
      text-align: center;
      font-size: 0.68rem;
      color: #9ca3af;
      padding: 0.3rem 0 0.5rem;
      letter-spacing: 0.03em;
    }

    @media (max-width: 480px) {
      #ok-chat-window { width: calc(100vw - 2.5rem); right: -0.5rem; }
      #ok-chat-widget { right: 1rem; bottom: 1rem; }
    }
  `;
  document.head.appendChild(style);

  /* ── Inject HTML ───────────────────────────────────────────────────── */
  const widget = document.createElement("div");
  widget.id = "ok-chat-widget";
  widget.innerHTML = `
    <div id="ok-chat-tooltip">Ask Onekey AI</div>
    <div id="ok-chat-window" role="dialog" aria-label="Onekey AI Chatbot">
      <div id="ok-chat-header">
        <img class="ok-avatar" src="/static/static/images/chat_dp.png" alt="Onekey AI" />
        <div>
          <div class="ok-title">Onekey AI Assistant</div>
          <div class="ok-subtitle"><span class="ok-status-dot"></span>Powered by Groq · LangChain</div>
        </div>
      </div>
      <div id="ok-chat-messages" aria-live="polite"></div>
      <div id="ok-chat-footer">
        <textarea
          id="ok-chat-input"
          rows="1"
          placeholder="Ask about your keys, usage, logs…"
          aria-label="Chat input"
        ></textarea>
        <button id="ok-chat-send" aria-label="Send message">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
      <div class="ok-powered">Onekey AI · RAG · NeonDB</div>
    </div>
    <button id="ok-chat-btn" aria-label="Open AI Chat" aria-expanded="false">
      <span class="ok-btn-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </span>
      <span class="ok-btn-close">✕</span>
    </button>
  `;
  document.body.appendChild(widget);

  /* ── State & DOM refs ──────────────────────────────────────────────── */
  const btn = document.getElementById("ok-chat-btn");
  const window_ = document.getElementById("ok-chat-window");
  const messages = document.getElementById("ok-chat-messages");
  const input = document.getElementById("ok-chat-input");
  const sendBtn = document.getElementById("ok-chat-send");
  let isOpen = false;
  let isThinking = false;

  /* ── Welcome message ───────────────────────────────────────────────── */
  addBotMessage("👋 Hi! I'm the Onekey AI Assistant. Ask me anything about your API keys, usage logs, providers, or errors — I query your live database to answer.");

  /* ── Toggle chat window ────────────────────────────────────────────── */
  btn.addEventListener("click", () => {
    isOpen = !isOpen;
    btn.classList.toggle("open", isOpen);
    btn.setAttribute("aria-expanded", isOpen);
    widget.classList.toggle("chat-open", isOpen);
    window_.classList.toggle("visible", isOpen);
    if (isOpen) {
      setTimeout(() => input.focus(), 250);
      scrollBottom();
    }
  });

  /* ── Close on outside click ─────────────────────────────────────────── */
  document.addEventListener("click", (e) => {
    if (isOpen && !widget.contains(e.target)) {
      isOpen = false;
      btn.classList.remove("open");
      btn.setAttribute("aria-expanded", false);
      widget.classList.remove("chat-open");
      window_.classList.remove("visible");
    }
  });

  /* ── Send on Enter (Shift+Enter = newline) ─────────────────────────── */
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  sendBtn.addEventListener("click", sendMessage);

  /* ── Auto-resize textarea ───────────────────────────────────────────── */
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 100) + "px";
  });

  /* ── Core send logic ───────────────────────────────────────────────── */
  async function sendMessage() {
    const question = input.value.trim();
    if (!question || isThinking) return;

    addUserMessage(question);
    input.value = "";
    input.style.height = "auto";

    isThinking = true;
    sendBtn.disabled = true;
    const thinkingEl = addThinkingIndicator();

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      thinkingEl.remove();
      if (!res.ok) {
        const err = await res.text();
        addBotMessage(`⚠️ Error ${res.status}: ${err}`);
      } else {
        const data = await res.json();
        addBotMessage(data.answer || "No answer returned.");
      }
    } catch (err) {
      thinkingEl.remove();
      addBotMessage(`⚠️ Could not reach the server. Make sure the backend is running. (${err.message})`);
    } finally {
      isThinking = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  /* ── DOM helpers ───────────────────────────────────────────────────── */
  function addUserMessage(text) {
    const el = document.createElement("div");
    el.className = "ok-msg ok-msg-user";
    el.textContent = text;
    messages.appendChild(el);
    scrollBottom();
  }

  function addBotMessage(text) {
    const el = document.createElement("div");
    el.className = "ok-msg ok-msg-bot";
    el.textContent = text;
    messages.appendChild(el);
    scrollBottom();
    return el;
  }

  function addThinkingIndicator() {
    const el = document.createElement("div");
    el.className = "ok-msg ok-msg-bot ok-thinking";
    el.innerHTML = `<span class="ok-dots"><span></span><span></span><span></span></span> Thinking…`;
    messages.appendChild(el);
    scrollBottom();
    return el;
  }

  function scrollBottom() {
    requestAnimationFrame(() => {
      messages.scrollTop = messages.scrollHeight;
    });
  }
})();
