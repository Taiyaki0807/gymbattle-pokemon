(() => {
  document.documentElement.classList.add('js');
  const status = document.getElementById('save-status');
  let pending = 0;
  const failed = new Set();
  function report() {
    status.textContent = failed.size ? '保存できない変更があります。赤い枠の入力を確認して「再保存」を押してください。' : pending ? '保存中…' : '変更を保存しました。';
    status.classList.toggle('save-error', failed.size > 0);
  }
  async function send(form) {
    const response = await fetch(form.action, {method: 'POST', body: new FormData(form), headers: {'Accept': 'application/json'}});
    if (response.redirected) throw new Error('ログインの有効期限が切れました。別のタブでログイン後に再保存してください。');
    let data;
    try { data = await response.json(); } catch { throw new Error('通信に失敗しました。再保存してください。'); }
    if (!response.ok) throw new Error(data.errors ? Object.values(data.errors).flat().join(' ') : '保存できませんでした。');
    return data;
  }
  document.querySelectorAll('.inline-form').forEach(form => {
    let busy = false;
    let dirty = false;
    const feedback = document.createElement('small');
    feedback.className = 'field-feedback';
    feedback.setAttribute('role', 'status');
    form.append(feedback);
    const retry = form.querySelector('.inline-save');
    async function save() {
      dirty = true;
      if (busy) return;
      busy = true;
      pending++;
      report();
      try {
        while (dirty) {
          dirty = false;
          await send(form);
        }
        failed.delete(form);
        feedback.textContent = '';
        form.classList.remove('has-error');
      } catch (error) {
        failed.add(form);
        feedback.textContent = error.message;
        form.classList.add('has-error');
        retry.textContent = '再保存';
      } finally {
        busy = false;
        pending--;
        report();
      }
    }
    form.addEventListener('change', () => {
      const select = form.querySelector('.symbol-select');
      if (select) select.className = 'symbol-select ' + select.value;
      save();
    });
    form.addEventListener('submit', event => { event.preventDefault(); save(); });
  });
  document.querySelectorAll('.add-member').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault();
    if (pending || failed.size) {
      status.textContent = '先に編集中の内容を保存してください。';
      return;
    }
    const button = form.querySelector('button');
    button.disabled = true;
    status.textContent = 'メンバーを追加中…';
    try {
      const data = await send(form);
      window.location.assign('/?added=' + data.id + '#member-' + data.id);
    } catch (error) {
      status.textContent = error.message;
      status.classList.add('save-error');
      button.disabled = false;
    }
  }));
  window.addEventListener('beforeunload', event => {
    if (pending || failed.size) { event.preventDefault(); event.returnValue = ''; }
  });
  const added = new URLSearchParams(window.location.search).get('added');
  if (added && /^\d+$/.test(added)) {
    const input = document.getElementById('name-' + added);
    if (input) { input.focus(); input.select(); }
  }
})();
