const state = {
  jobs: [],
  sourceHealth: [],
  visibleLimit: 20,
  saved: new Set(JSON.parse(localStorage.getItem('savedJobs') || '[]')),
};

const $ = (id) => document.getElementById(id);
const els = {
  jobList: $('jobList'), jobCount: $('jobCount'), newCount: $('newCount'), sourceCount: $('sourceCount'),
  updatedAt: $('updatedAt'), visibleCount: $('visibleCount'), sourceHealth: $('sourceHealth'),
  searchInput: $('searchInput'), locationFilter: $('locationFilter'), categoryFilter: $('categoryFilter'),
  freshOnly: $('freshOnly'), openOnly: $('openOnly'), newGradOnly: $('newGradOnly'),
  highMatchOnly: $('highMatchOnly'), savedOnly: $('savedOnly'), sortOrder: $('sortOrder'),
  loadMore: $('loadMore'), emptyState: $('emptyState'), resetFilters: $('resetFilters'),
  activeFilters: $('activeFilters'), themeToggle: $('themeToggle'), template: $('jobCardTemplate')
};

const DAY = 86400000;
const now = () => new Date();
const parseDate = (value) => value ? new Date(`${value}T12:00:00`) : null;
const daysSince = (value) => value ? Math.floor((now() - parseDate(value)) / DAY) : 9999;
const daysUntil = (value) => value ? Math.ceil((parseDate(value) - now()) / DAY) : 9999;
const fmtDate = (value) => value ? new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric', year: 'numeric' }).format(parseDate(value)) : 'Not listed';
const escapeText = (value) => String(value ?? '').trim();

function loadTheme() {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('theme', next);
}

async function loadData() {
  try {
    const [jobsResponse, healthResponse] = await Promise.all([
      fetch(`data/jobs.json?v=${Date.now()}`),
      fetch(`data/source_health.json?v=${Date.now()}`),
    ]);
    const jobsPayload = await jobsResponse.json();
    const healthPayload = await healthResponse.json();
    state.jobs = jobsPayload.jobs || [];
    state.sourceHealth = healthPayload.sources || [];
    updateHero(jobsPayload);
    render();
    renderSourceHealth();
  } catch (error) {
    els.jobList.innerHTML = `<div class="empty-state"><h3>Job data could not be loaded</h3><p>${error.message}</p></div>`;
  }
}

function updateHero(payload) {
  const newJobs = state.jobs.filter(job => daysSince(job.posted_date) <= 7).length;
  const activeSources = state.sourceHealth.filter(source => source.status === 'ok').length;
  els.jobCount.textContent = state.jobs.length.toLocaleString();
  els.newCount.textContent = newJobs.toLocaleString();
  els.sourceCount.textContent = activeSources.toLocaleString();
  const updated = payload.generated_at ? new Date(payload.generated_at) : null;
  els.updatedAt.textContent = updated ? new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric' }).format(updated) : 'Unknown';
}

function currentFilters() {
  return {
    search: els.searchInput.value.trim().toLowerCase(),
    location: els.locationFilter.value,
    category: els.categoryFilter.value,
    fresh: els.freshOnly.checked,
    open: els.openOnly.checked,
    newGrad: els.newGradOnly.checked,
    highMatch: els.highMatchOnly.checked,
    saved: els.savedOnly.checked,
    sort: els.sortOrder.value,
  };
}

function matchesLocation(job, location) {
  if (location === 'all') return true;
  return job.region === location;
}

function filterJobs() {
  const filters = currentFilters();
  let jobs = state.jobs.filter(job => {
    const haystack = [job.title, job.company, job.location, job.description, ...(job.skills || []), ...(job.categories || [])].join(' ').toLowerCase();
    const notExpired = !job.closing_date || daysUntil(job.closing_date) >= 0;
    return (!filters.search || haystack.includes(filters.search))
      && matchesLocation(job, filters.location)
      && (filters.category === 'all' || (job.categories || []).includes(filters.category))
      && (!filters.fresh || daysSince(job.posted_date) <= 14)
      && (!filters.open || notExpired)
      && (!filters.newGrad || job.new_grad_friendly)
      && (!filters.highMatch || Number(job.match_score || 0) >= 70)
      && (!filters.saved || state.saved.has(job.id));
  });

  jobs.sort((a, b) => {
    if (filters.sort === 'newest') return (b.posted_date || '').localeCompare(a.posted_date || '') || (b.match_score - a.match_score);
    if (filters.sort === 'deadline') return daysUntil(a.closing_date) - daysUntil(b.closing_date) || (b.match_score - a.match_score);
    if (filters.sort === 'company') return a.company.localeCompare(b.company) || a.title.localeCompare(b.title);
    return (b.match_score - a.match_score) || (b.posted_date || '').localeCompare(a.posted_date || '');
  });
  return jobs;
}

function makeBadge(text, className = '') {
  const span = document.createElement('span');
  span.className = `badge ${className}`.trim();
  span.textContent = text;
  return span;
}

function jobCard(job) {
  const fragment = els.template.content.cloneNode(true);
  const card = fragment.querySelector('.job-card');
  const title = fragment.querySelector('.job-title');
  const badges = fragment.querySelector('.badge-row');
  const save = fragment.querySelector('.save-button');
  title.textContent = escapeText(job.title);
  title.href = job.url;
  fragment.querySelector('.company-location').textContent = `${escapeText(job.company)} · ${escapeText(job.location)}`;
  fragment.querySelector('.job-summary').textContent = escapeText(job.description || 'Open the posting for full role details.');
  fragment.querySelector('.source-label').textContent = `Source: ${escapeText(job.source)}`;
  const apply = fragment.querySelector('.apply-link');
  apply.href = job.url;

  badges.append(makeBadge(`${Math.round(job.match_score || 0)}% match`, 'match'));
  if (daysSince(job.posted_date) <= 7) badges.append(makeBadge('New', 'fresh'));
  if (job.new_grad_friendly) badges.append(makeBadge('Early career'));
  const deadlineDays = daysUntil(job.closing_date);
  if (deadlineDays >= 0 && deadlineDays <= 7) badges.append(makeBadge(`${deadlineDays}d left`, 'deadline'));

  const reasons = fragment.querySelector('.match-reasons');
  (job.match_reasons || []).slice(0, 4).forEach(reason => {
    const el = document.createElement('span');
    el.className = 'reason';
    el.textContent = `✓ ${reason}`;
    reasons.append(el);
  });

  const skills = fragment.querySelector('.skill-row');
  (job.skills || []).slice(0, 7).forEach(skill => {
    const el = document.createElement('span');
    el.className = 'skill';
    el.textContent = skill;
    skills.append(el);
  });

  const meta = fragment.querySelector('.job-meta');
  [
    job.posted_date && `Posted ${fmtDate(job.posted_date)}`,
    job.closing_date && `Closes ${fmtDate(job.closing_date)}`,
    job.salary,
    job.workplace,
    job.employment_type,
  ].filter(Boolean).forEach(item => meta.append(makeBadge(item)));

  const syncSaved = () => {
    const saved = state.saved.has(job.id);
    save.textContent = saved ? '★' : '☆';
    save.classList.toggle('saved', saved);
    save.setAttribute('aria-label', saved ? 'Remove saved job' : 'Save job');
  };
  syncSaved();
  save.addEventListener('click', () => {
    if (state.saved.has(job.id)) state.saved.delete(job.id); else state.saved.add(job.id);
    localStorage.setItem('savedJobs', JSON.stringify([...state.saved]));
    syncSaved();
    if (els.savedOnly.checked) render();
  });
  card.dataset.jobId = job.id;
  return fragment;
}

function renderActiveFilters() {
  const filters = currentFilters();
  const chips = [];
  if (filters.search) chips.push(`Search: ${filters.search}`);
  if (filters.location !== 'all') chips.push(filters.location);
  if (filters.category !== 'all') chips.push(filters.category);
  if (filters.fresh) chips.push('Last 14 days');
  if (filters.newGrad) chips.push('New-grad friendly');
  if (filters.highMatch) chips.push('70%+ match');
  if (filters.saved) chips.push('Saved');
  els.activeFilters.replaceChildren(...chips.map(text => {
    const chip = document.createElement('span');
    chip.className = 'filter-chip';
    chip.textContent = text;
    return chip;
  }));
}

function render() {
  const filtered = filterJobs();
  const visible = filtered.slice(0, state.visibleLimit);
  els.jobList.replaceChildren(...visible.map(jobCard));
  els.visibleCount.textContent = `${filtered.length.toLocaleString()} result${filtered.length === 1 ? '' : 's'}`;
  els.loadMore.hidden = visible.length >= filtered.length;
  els.emptyState.hidden = filtered.length !== 0;
  renderActiveFilters();
}

function renderSourceHealth() {
  els.sourceHealth.replaceChildren(...state.sourceHealth.map(source => {
    const card = document.createElement('article');
    card.className = 'source-card';
    const errorText = source.error ? ` · ${source.error}` : '';
    card.innerHTML = `<div class="source-card-top"><h3>${escapeText(source.name)}</h3><span class="status ${escapeText(source.status)}">${escapeText(source.status)}</span></div><p>${Number(source.kept || 0).toLocaleString()} relevant jobs kept from ${Number(source.fetched || 0).toLocaleString()} fetched${errorText}</p>`;
    return card;
  }));
}

function resetFilters() {
  els.searchInput.value = '';
  els.locationFilter.value = 'all';
  els.categoryFilter.value = 'all';
  els.freshOnly.checked = false;
  els.openOnly.checked = true;
  els.newGradOnly.checked = false;
  els.highMatchOnly.checked = false;
  els.savedOnly.checked = false;
  els.sortOrder.value = 'match';
  state.visibleLimit = 20;
  render();
}

[els.searchInput, els.locationFilter, els.categoryFilter, els.freshOnly, els.openOnly, els.newGradOnly, els.highMatchOnly, els.savedOnly, els.sortOrder]
  .forEach(el => el.addEventListener(el.tagName === 'INPUT' && el.type === 'search' ? 'input' : 'change', () => { state.visibleLimit = 20; render(); }));
els.loadMore.addEventListener('click', () => { state.visibleLimit += 20; render(); });
els.resetFilters.addEventListener('click', resetFilters);
els.themeToggle.addEventListener('click', toggleTheme);
loadTheme();
loadData();
