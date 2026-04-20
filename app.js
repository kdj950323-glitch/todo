class TodoApp {
  constructor() {
    this.todos = [];
    this.filter = 'all';
    this.theme = 'light';
    this.editingId = null;
    this.dragSrcId = null;

    this.loadFromStorage();
    this.cacheElements();
    this.bindStaticEvents();
    this.setDate();
    this.applyTheme();
    this.render();
  }

  // ── Storage ──────────────────────────────────────────

  loadFromStorage() {
    try {
      const raw = localStorage.getItem('todoapp-v1');
      if (raw) {
        const data = JSON.parse(raw);
        this.todos = Array.isArray(data.todos) ? data.todos : [];
        this.theme = data.theme === 'dark' ? 'dark' : 'light';
      }
    } catch {
      this.todos = [];
    }
  }

  save() {
    localStorage.setItem('todoapp-v1', JSON.stringify({
      todos: this.todos,
      theme: this.theme,
    }));
  }

  // ── DOM refs ─────────────────────────────────────────

  cacheElements() {
    this.form         = document.getElementById('add-form');
    this.input        = document.getElementById('todo-input');
    this.prioritySel  = document.getElementById('priority-select');
    this.dueDateInput = document.getElementById('due-date-input');
    this.listEl       = document.getElementById('todo-list');
    this.statsEl      = document.getElementById('stats-text');
    this.clearBtn     = document.getElementById('clear-completed');
    this.themeBtn     = document.getElementById('theme-toggle');
    this.emptyEl      = document.getElementById('empty-state');
  }

  // ── Static event bindings ─────────────────────────────

  bindStaticEvents() {
    this.form.addEventListener('submit', e => { e.preventDefault(); this.addTodo(); });
    this.clearBtn.addEventListener('click', () => this.clearCompleted());
    this.themeBtn.addEventListener('click', () => this.toggleTheme());

    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filter = tab.dataset.filter;
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.render();
      });
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && this.editingId) {
        this.editingId = null;
        this.render();
      }
    });
  }

  // ── CRUD ─────────────────────────────────────────────

  addTodo() {
    const text = this.input.value.trim();
    if (!text) { this.input.focus(); return; }

    this.todos.unshift({
      id:        String(Date.now()),
      text,
      completed: false,
      priority:  this.prioritySel.value,
      dueDate:   this.dueDateInput.value || null,
      createdAt: new Date().toISOString(),
    });

    this.input.value       = '';
    this.prioritySel.value = 'none';
    this.dueDateInput.value = '';
    this.save();
    this.render();
    this.input.focus();
  }

  toggleTodo(id) {
    const todo = this.todos.find(t => t.id === id);
    if (todo) { todo.completed = !todo.completed; this.save(); this.render(); }
  }

  deleteTodo(id) {
    const el = this.listEl.querySelector(`[data-id="${id}"]`);
    const doRemove = () => {
      this.todos = this.todos.filter(t => t.id !== id);
      this.save();
      this.render();
    };
    if (el) {
      el.classList.add('removing');
      setTimeout(doRemove, 220);
    } else {
      doRemove();
    }
  }

  startEdit(id) {
    this.editingId = id;
    this.render();
    const inp = this.listEl.querySelector('.edit-input');
    if (inp) { inp.focus(); inp.select(); }
  }

  commitEdit(id, value) {
    const text = value.trim();
    if (text) {
      const todo = this.todos.find(t => t.id === id);
      if (todo) todo.text = text;
    }
    this.editingId = null;
    this.save();
    this.render();
  }

  clearCompleted() {
    this.todos = this.todos.filter(t => !t.completed);
    this.save();
    this.render();
  }

  // ── Filtering ─────────────────────────────────────────

  filtered() {
    if (this.filter === 'active')    return this.todos.filter(t => !t.completed);
    if (this.filter === 'completed') return this.todos.filter(t => t.completed);
    return this.todos;
  }

  // ── Theme ─────────────────────────────────────────────

  toggleTheme() {
    this.theme = this.theme === 'light' ? 'dark' : 'light';
    this.save();
    this.applyTheme();
  }

  applyTheme() {
    document.documentElement.setAttribute('data-theme', this.theme);
  }

  // ── Date helpers ──────────────────────────────────────

  setDate() {
    const el = document.getElementById('current-date');
    if (el) el.textContent = new Date().toLocaleDateString('ko-KR', {
      year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
    });
  }

  formatDue(dateStr) {
    if (!dateStr) return null;
    const due   = new Date(dateStr + 'T00:00:00');
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const diff  = Math.round((due - today) / 86400000);
    if (diff < 0)  return { text: `${Math.abs(diff)}일 지남`, overdue: true };
    if (diff === 0) return { text: '오늘 마감', overdue: false };
    if (diff === 1) return { text: '내일 마감', overdue: false };
    return {
      text: `${due.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })} 마감`,
      overdue: false,
    };
  }

  // ── Drag & Drop ───────────────────────────────────────

  onDragStart(e, id) {
    this.dragSrcId = id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
    requestAnimationFrame(() => {
      const el = this.listEl.querySelector(`[data-id="${id}"]`);
      if (el) el.classList.add('dragging');
    });
  }

  onDragOver(e, id) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    this.listEl.querySelectorAll('.todo-item').forEach(el => el.classList.remove('drag-over'));
    const el = this.listEl.querySelector(`[data-id="${id}"]`);
    if (el) el.classList.add('drag-over');
  }

  onDrop(e, targetId) {
    e.preventDefault();
    if (!this.dragSrcId || this.dragSrcId === targetId) return;
    const srcIdx = this.todos.findIndex(t => t.id === this.dragSrcId);
    const tgtIdx = this.todos.findIndex(t => t.id === targetId);
    if (srcIdx === -1 || tgtIdx === -1) return;
    const [item] = this.todos.splice(srcIdx, 1);
    this.todos.splice(tgtIdx, 0, item);
    this.dragSrcId = null;
    this.save();
    this.render();
  }

  onDragEnd() {
    this.listEl.querySelectorAll('.todo-item')
      .forEach(el => el.classList.remove('dragging', 'drag-over'));
    this.dragSrcId = null;
  }

  // ── Render ────────────────────────────────────────────

  render() {
    const items       = this.filtered();
    const activeCount = this.todos.filter(t => !t.completed).length;
    const doneCount   = this.todos.filter(t => t.completed).length;

    this.statsEl.textContent = `${activeCount}개 남음`;
    this.clearBtn.style.visibility = doneCount > 0 ? 'visible' : 'hidden';

    if (items.length === 0) {
      this.listEl.innerHTML = '';
      this.emptyEl.hidden = false;
      return;
    }

    this.emptyEl.hidden = true;
    this.listEl.innerHTML = items.map(t => this.renderItem(t)).join('');
    this.bindItemEvents();
  }

  renderItem(todo) {
    const due       = this.formatDue(todo.dueDate);
    const editing   = this.editingId === todo.id;
    const priAttr   = todo.priority !== 'none' ? ` data-priority="${todo.priority}"` : '';
    const completed = todo.completed ? ' completed' : '';

    return `
      <li class="todo-item${completed}" data-id="${todo.id}"${priAttr} draggable="${editing ? 'false' : 'true'}">
        <div class="todo-checkbox${todo.completed ? ' checked' : ''}" data-action="toggle" data-id="${todo.id}"></div>
        <div class="todo-content">
          ${editing
            ? `<input class="edit-input" type="text" value="${this.esc(todo.text)}" data-id="${todo.id}" maxlength="200">`
            : `<span class="todo-text">${this.esc(todo.text)}</span>`}
          ${due ? `<span class="todo-due${due.overdue ? ' overdue' : ''}">${due.text}</span>` : ''}
        </div>
        <div class="todo-actions">
          <button class="action-btn" data-action="edit" data-id="${todo.id}" title="수정">✎</button>
          <button class="action-btn delete" data-action="delete" data-id="${todo.id}" title="삭제">✕</button>
        </div>
      </li>`;
  }

  esc(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  bindItemEvents() {
    // Action buttons & checkboxes
    this.listEl.querySelectorAll('[data-action]').forEach(el => {
      el.addEventListener('click', e => {
        e.stopPropagation();
        const { action, id } = el.dataset;
        if (action === 'toggle') this.toggleTodo(id);
        else if (action === 'edit') this.startEdit(id);
        else if (action === 'delete') this.deleteTodo(id);
      });
    });

    // Edit input
    const editInp = this.listEl.querySelector('.edit-input');
    if (editInp) {
      editInp.addEventListener('keydown', e => {
        if (e.key === 'Enter')  this.commitEdit(editInp.dataset.id, editInp.value);
        if (e.key === 'Escape') { this.editingId = null; this.render(); }
      });
      editInp.addEventListener('blur', () => {
        setTimeout(() => {
          if (this.editingId) this.commitEdit(editInp.dataset.id, editInp.value);
        }, 150);
      });
    }

    // Drag & Drop
    this.listEl.querySelectorAll('.todo-item').forEach(item => {
      const id = item.dataset.id;
      item.addEventListener('dragstart', e => this.onDragStart(e, id));
      item.addEventListener('dragover',  e => this.onDragOver(e, id));
      item.addEventListener('drop',      e => this.onDrop(e, id));
      item.addEventListener('dragend',   () => this.onDragEnd());
    });
  }
}

document.addEventListener('DOMContentLoaded', () => new TodoApp());
