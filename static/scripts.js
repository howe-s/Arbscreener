/* Cost assumptions are local to a scan; market economics come from the server. */
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[ch]));
}
function sanitizeOpportunity(raw) {
  return Object.fromEntries(Object.entries(raw).map(([key, value]) => [key,
    escapeHtml(key.endsWith('_url') && !/^https?:\/\//i.test(String(value)) ? '#' : value)]));
}
function costNumber(value) {
  if (!['number','string'].includes(typeof value) || (typeof value === 'string' && value.trim() === '') || value === null || value === undefined || typeof value === 'boolean') return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}
function calculateEconomics(source = {}, costs = {}, minimumMargin = 1) {
  const investment = costNumber(source.investment), revenue = costNumber(source.revenue), fees = costNumber(source.fees);
  const gas = costNumber(costs.gas), transfer = costNumber(costs.transfer);
  const missing = [];
  for (const [label, value] of [['Investment', investment], ['Expected proceeds', revenue], ['Trading fees', fees], ['Gas / network cost', gas], ['Transfer / other cost', transfer]]) {
    if (value === null) missing.push(label);
  }
  const known = investment !== null && revenue !== null && fees !== null;
  let subtotal = known ? investment + fees + (gas ?? 0) + (transfer ?? 0) : null;
  if (subtotal !== null && !Number.isFinite(subtotal)) {subtotal = null; missing.push('A supported cost total');}
  const estimate = known && subtotal !== null ? revenue - subtotal : null;
  const complete = missing.length === 0;
  const margin = estimate !== null && revenue > 0 ? estimate / revenue * 100 : null;
  let status = 'review', reason;
  if (estimate !== null && estimate < -0.005) {
    status = 'unprofitable'; reason = 'Known costs already exceed expected proceeds.';
  } else if (!complete) {
    reason = missing.join(' + ') + ' unknown.';
  } else if (estimate <= 0.005) {
    reason = 'At break-even. There is no room for execution costs to increase.';
  } else if (margin < minimumMargin) {
    reason = `Below your ${minimumMargin}% minimum margin.`;
  } else {
    status = 'profitable'; reason = 'All cost assumptions entered. Your margin target is met.';
  }
  return {investment, revenue, fees, gas, transfer, subtotal, estimate, margin, complete,
    total: complete ? subtotal : null, net: complete ? estimate : null, missing, status, reason};
}
function compareOpportunities(a, b) {
  const rank = {profitable: 0, review: 1, unprofitable: 2};
  return rank[a.e.status] - rank[b.e.status] || Number(b.e.complete) - Number(a.e.complete) ||
    (b.e.estimate ?? -Infinity) - (a.e.estimate ?? -Infinity) || (b.e.margin ?? -Infinity) - (a.e.margin ?? -Infinity) || a.id - b.id;
}
const dollars = value => value === null || !Number.isFinite(value) ? 'Unknown' : new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', maximumFractionDigits:2}).format(value);
const signedDollars = value => value === null ? 'Unknown' : (value > 0 ? '+' : '') + dollars(value);

function startDashboard() {
  const form = document.querySelector('#scan-form'), list = document.querySelector('#opportunities');
  const message = document.querySelector('#message'), scanButton = document.querySelector('#scan-button');
  let rows = [], scanned = false, activeFilter = 'all', limit = 20, minimumMargin = 1;
  const costAssumptions = new Map(), openDetails = new Set();
  const labels = {profitable: 'PROFITABLE', review: 'REVIEW', unprofitable: 'NOT PROFITABLE'};
  function poolDetails(raw) {
    const o = sanitizeOpportunity(raw);
    return [1,2,3].filter(n => raw[`pair${n}`]).map(n => `<div class="pool"><strong>Pool ${n} · ${o[`pair${n}`]}</strong><p>${o[`pair${n}_dex_id`]} · ${o[`pair${n}_chain_id`]}</p><p>Base token price: ${escapeHtml(dollars(Number(raw[`pair${n}_price`])))}</p><p>Pool liquidity: ${o[`pair${n}_liquidity`]}</p><code>${o[`pool_pair${n}_address`]}</code><p><a href="${o[`pool_pair${n}_url`]}" target="_blank" rel="noopener noreferrer">Inspect pool ↗</a></p></div>`).join('');
  }
  function card(row) {
    const {raw, e, id} = row, o = sanitizeOpportunity(raw), costs = costAssumptions.get(id) || {};
    const title = raw.pair1 || 'Trading route';
    const action = e.status === 'unprofitable' ? 'Review calculation' : e.status === 'profitable' ? 'Review trade' : !e.complete ? 'Resolve missing costs' : 'Review calculation';
    return `<article class="opportunity ${e.status}" data-id="${id}" aria-label="${escapeHtml(title)}">
      <div class="card-main"><div><span class="badge">${labels[e.status]}</span><h3>${escapeHtml(title)}</h3><p class="route-meta">${o.pair1_chain_id} · ${raw.pair3 ? '3-trade cycle' : '2-trade route'} · ${o.pair1_dex_id} / ${o.pair2_dex_id}</p>
</div>
      <div class="profit-block"><p class="profit-caption">ESTIMATED NET PROFIT</p><strong class="net-profit">${signedDollars(e.estimate)}</strong><p class="profit-note">${e.complete ? 'Based on your cost assumptions' : 'Before missing costs · not a final net'}</p></div>
      <dl class="economics"><div><dt>Expected proceeds</dt><dd>${dollars(e.revenue)}</dd></div><div><dt>Total cost${!e.complete ? ' · incomplete' : ''}</dt><dd>${e.complete ? dollars(e.total) : dollars(e.subtotal) + ' + ?'}</dd></div><div><dt>${e.complete ? 'Net margin' : 'Margin before missing costs'}</dt><dd>${e.margin === null ? 'Unknown' : (Math.abs(e.margin) > 0 && Math.abs(e.margin) < .01 ? e.margin.toPrecision(2) : e.margin.toFixed(2)) + '%'}</dd></div></dl>
      </div>
      <div class="notice"><span class="notice-icon" aria-hidden="true">${e.status === 'profitable' ? '✓' : 'ⓘ'}</span><p>${escapeHtml(e.reason)}${e.status === 'unprofitable' && !e.complete ? ' Additional costs are still unknown.' : ''}</p></div>
      <details class="route-details" data-id="${id}" ${openDetails.has(id) ? 'open' : ''}><summary>${action} <span aria-hidden="true">↗</span></summary><div class="detail-content">
      <h4>Complete the cost picture</h4><p class="detail-copy">Enter the total USD cost for this route. Enter 0 only if you have verified that no cost applies. Saved assumptions are estimates, not confirmed trade results.</p>
      <form class="cost-form" data-id="${id}"><label>Gas / network cost · USD<input name="gas" type="number" min="0" step="0.01" placeholder="Unknown" value="${escapeHtml(costs.gas ?? '')}"></label><label>Transfer / other cost · USD<input name="transfer" type="number" min="0" step="0.01" placeholder="Unknown" value="${escapeHtml(costs.transfer ?? '')}"></label><button type="submit">Update calculation</button></form>
      <div class="breakdown"><div><p>Investment</p><strong>${dollars(e.investment)}</strong></div><div><p>Trading fees · estimated</p><strong>${dollars(e.fees)}</strong></div><div><p>Gas / network</p><strong>${dollars(e.gas)}</strong></div><div><p>Transfer / other</p><strong>${dollars(e.transfer)}</strong></div></div>
      <p class="detail-copy">Expected proceeds include modeled slippage, before trading fees. Net profit = proceeds − investment − fees − gas − other costs. Margin = net profit ÷ proceeds. Target: ${minimumMargin}%. Quotes and actual price impact can change before execution.</p>
      <h4>Investigate the pools</h4><div class="pools">${poolDetails(raw)}</div></div></details></article>`;
  }
  function render() {
    const enriched = rows.map((raw, id) => ({raw, id, e:calculateEconomics(raw.economics, costAssumptions.get(id), minimumMargin)})).sort(compareOpportunities);
    const counts = {all:enriched.length, profitable:0, review:0, unprofitable:0};
    let potential = 0;
    enriched.forEach(row => {counts[row.e.status]++; if(row.e.status === 'profitable') potential += row.e.net;});
    document.querySelector('#metric-all').textContent = counts.all;
    document.querySelector('#metric-profitable').textContent = counts.profitable;
    document.querySelector('#metric-review').textContent = counts.review;
    document.querySelector('#metric-profit').textContent = dollars(potential);
    document.querySelectorAll('[data-filter]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.filter === activeFilter));
      button.querySelector('span').textContent = counts[button.dataset.filter];
    });
    const filtered = enriched.filter(row => activeFilter === 'all' || row.e.status === activeFilter);
    document.querySelector('#result-count').textContent = `${filtered.length} of ${counts.all} routes · all returns are estimates`;
    list.innerHTML = filtered.length ? filtered.slice(0, limit).map(card).join('') : `<div class="empty-state"><h3>${counts.all ? 'No routes in this view.' : 'No comparable routes found.'}</h3><p>${counts.all ? 'Try another filter or resolve missing costs on a route.' : 'Try a different token. Only liquid, same-chain routes are compared.'}</p></div>`;
    document.querySelector('#pagination').innerHTML = filtered.length > limit ? `<button type="button" id="show-more">Show next ${Math.min(20, filtered.length-limit)} routes</button>` : '';
  }
  form.addEventListener('input', () => {if(scanned) {message.className = ''; message.textContent = 'Settings changed. Scan again to update these results.';}});
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(form);
    const requestedMargin = Number(data.get('minimum_margin'));
    form.querySelectorAll('input').forEach(input => input.disabled = true);
    data.set('slippage', Number(data.get('slippage')) / 100);
    data.set('fee_percentage', Number(data.get('fee_percentage')) / 100);
    data.set('include_unprofitable', 'true');
    scanButton.disabled = true; scanButton.textContent = 'Scanning…';
    list.setAttribute('aria-busy','true'); message.className = ''; message.textContent = 'Comparing routes and calculating returns…';
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 120000);
    try {
      const response = await fetch(form.action, {method:'POST', body:data, signal:controller.signal});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Scan failed. Please try again.');
      if (!Array.isArray(result)) throw new Error('The scan returned an unexpected response.');
      minimumMargin = requestedMargin; rows = result; scanned = true; limit = 20; activeFilter = 'all'; costAssumptions.clear(); openDetails.clear();
      render(); message.textContent = `Scan complete · ${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} · Costs are unknown until you enter them.`;
    } catch(error) {
      message.className = 'error'; message.textContent = (error.name === 'AbortError' ? 'The scan took too long. Please try again.' : error.message) + (scanned ? ' Previous results are still shown.' : '');
    } finally {
      clearTimeout(timeout); form.querySelectorAll('input').forEach(input => input.disabled = false); scanButton.disabled = false; scanButton.innerHTML = 'Find opportunities <span aria-hidden="true">↗</span>'; list.setAttribute('aria-busy','false');
    }
  });
  document.querySelector('.filters').addEventListener('click', event => {
    const button = event.target.closest('[data-filter]');
    if(button && scanned) {activeFilter = button.dataset.filter; limit = 20; render();}
  });
  list.addEventListener('toggle', event => {
    const detail = event.target;
    if(detail.matches('.route-details')) {
      if(detail.open) openDetails.add(Number(detail.dataset.id)); else openDetails.delete(Number(detail.dataset.id));
    }
  }, true);
  list.addEventListener('submit', event => {
    const costsForm = event.target.closest('.cost-form');
    if(!costsForm) return;
    event.preventDefault();
    const id = Number(costsForm.dataset.id), data = new FormData(costsForm);
    costAssumptions.set(id, {gas:data.get('gas'), transfer:data.get('transfer')});
    openDetails.add(id); render();
    message.className = ''; message.textContent = 'Cost assumptions updated. Status, net profit and margin recalculated.';
    list.querySelector(`[data-id="${id}"] summary`)?.focus();
  });
  document.querySelector('#pagination').addEventListener('click', event => {if(event.target.closest('#show-more')) {limit += 20; render();}});
}
if (typeof module !== 'undefined') module.exports = {sanitizeOpportunity, calculateEconomics, compareOpportunities};
if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', startDashboard);
