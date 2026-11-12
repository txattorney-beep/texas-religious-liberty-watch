'use strict';
const newsSearch = document.querySelector('#news-search');
const newsCards = [...document.querySelectorAll('[data-news-title]')];
function filterNews() {
  const query = newsSearch.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const card of newsCards) {
    card.hidden = !query.split(/\s+/).filter(Boolean).every(term => card.dataset.newsTitle.toLocaleLowerCase().includes(term));
    if (!card.hidden) count += 1;
  }
  document.querySelector('#news-count').textContent = `${count} headline${count === 1 ? '' : 's'}${query ? ' matching your search' : ' from the past 30 days'}`;
  document.querySelector('#news-empty').hidden = count !== 0;
}
if (newsSearch) newsSearch.addEventListener('input', filterNews);
document.querySelector('#news-search-form')?.addEventListener('submit', event => { event.preventDefault(); filterNews(); });
const freshness = document.querySelector('#news-stale');
if (freshness) freshness.hidden = Date.now() - Date.parse(freshness.dataset.updated) <= 36 * 3600000;
