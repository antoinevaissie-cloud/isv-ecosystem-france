async function loadProfiles() {
  const res = await fetch('./data/isv_profiles.json');
  if (!res.ok) throw new Error('Failed to load data');
  const data = await res.json();
  return data.profiles || [];
}

function wordCount(str) {
  return (str.trim().match(/\b\w+\b/g) || []).length;
}

function renderCards(profiles, query = '') {
  const container = document.getElementById('cards');
  container.innerHTML = '';
  const q = query.trim().toLowerCase();

  const filtered = profiles.filter(p => {
    if (!q) return true;
    const hay = [p.name, ...(p.answers || []).flatMap(a => [a.question, a.answer])]
      .join(' \n ')
      .toLowerCase();
    return hay.includes(q);
  });

  document.getElementById('count').textContent = `${filtered.length} ISVs`;

  for (const p of filtered) {
    const card = document.createElement('article');
    card.className = 'card';
    const h2 = document.createElement('h2');
    h2.textContent = p.name;
    card.appendChild(h2);

    // Build Q&A lines and enforce 200-word cap for the whole card body
    const lines = (p.answers || []).map(a => ({
      q: a.question || '',
      a: a.answer || ''
    }));

    const ul = document.createElement('ul');
    ul.className = 'qa';

    let totalWords = 0;
    let trimmed = false;

    for (const { q, a } of lines) {
      if (!a) continue;
      const lineText = `${q ? q + ': ' : ''}${a}`;
      const wc = wordCount(lineText);
      if (totalWords + wc <= 200) {
        const li = document.createElement('li');
        li.innerHTML = q ? `<b>${q}:</b> ${a}` : a;
        ul.appendChild(li);
        totalWords += wc;
      } else {
        // Try to trim the answer to fit remaining words
        const remaining = Math.max(0, 200 - totalWords - wordCount(q ? q + ':' : ''));
        if (remaining > 0) {
          const words = a.split(/\s+/).slice(0, remaining).join(' ');
          const li = document.createElement('li');
          li.innerHTML = q ? `<b>${q}:</b> ${words}…` : `${words}…`;
          ul.appendChild(li);
        }
        trimmed = true;
        break;
      }
    }

    card.appendChild(ul);
    if (trimmed) {
      const note = document.createElement('div');
      note.className = 'trim-note';
      note.textContent = 'Trimmed to 200 words.';
      card.appendChild(note);
    }

    container.appendChild(card);
  }
}

(async () => {
  try {
    const profiles = await loadProfiles();
    const input = document.getElementById('search');
    renderCards(profiles);
    input.addEventListener('input', () => renderCards(profiles, input.value));
  } catch (e) {
    const container = document.getElementById('cards');
    container.innerHTML = `<div class="card"><h2>Error</h2><p>${e.message}</p></div>`;
    console.error(e);
  }
})();
