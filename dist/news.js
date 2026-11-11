'use strict';
const newsSearch = document.querySelector('#news-search');
const newsCards = [...document.querySelectorAll('[data-news-title]')];
if (newsSearch) newsSearch.addEventListener('input', () => {
  const query = newsSearch.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const card of newsCards) {
    card.hidden = !card.dataset.newsTitle.toLocaleLowerCase().includes(query);
    if (!card.hidden) count += 1;
  }
  document.querySelector('#news-count').textContent = `${count} headline${count === 1 ? '' : 's'}${query ? ' matching your search' : ' from the past 30 days'}`;
  document.querySelector('#news-empty').hidden = count !== 0;
});
const freshness = document.querySelector('#news-stale');
if (freshness) freshness.hidden = Date.now() - Date.parse(freshness.dataset.updated) <= 36 * 3600000;
