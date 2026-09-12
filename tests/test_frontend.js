const assert = require('node:assert/strict');
const {sanitizeOpportunity} = require('../static/scripts.js');
const result = sanitizeOpportunity({
  pair1: '<img src=x onerror="alert(1)">',
  pool_pair1_url: 'javascript:alert(1)',
  pool_pair2_url: 'https://example.com/?q=" onclick="alert(1)',
  profit: '$50.00',
});
assert.equal(result.pair1, '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
assert.equal(result.pool_pair1_url, '#');
assert.ok(!result.pool_pair2_url.includes('"'));
assert.equal(result.profit, '$50.00');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../templates/index.html'), 'utf8');
for (const [, source] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(source);
console.log('Frontend escaping and inline JavaScript syntax: PASS');

const {calculateEconomics, compareOpportunities} = require('../static/scripts.js');
const source = {investment:150, revenue:300, fees:12};
let economics = calculateEconomics(source, {gas:5, transfer:5});
assert.equal(economics.net, 128);
assert.equal(economics.total, 172);
assert.equal(economics.margin, 128/300*100);
assert.equal(economics.status, 'profitable');
assert.equal(calculateEconomics(source).status, 'review');
assert.equal(calculateEconomics(source).net, null);
assert.equal(calculateEconomics(source).total, null);
assert.equal(calculateEconomics(source).estimate, 138);
assert.equal(calculateEconomics(source, {gas:'', transfer:0}).status, 'review');
assert.equal(calculateEconomics(source, {gas:' ', transfer:0}).status, 'review');
assert.equal(calculateEconomics(source, {gas:'Infinity', transfer:0}).status, 'review');
assert.equal(calculateEconomics(source, {gas:-1, transfer:0}).status, 'review');
assert.equal(calculateEconomics(source, {gas:0, transfer:0}).status, 'profitable');
assert.equal(calculateEconomics({...source, fees:null}, {gas:0, transfer:0}).status, 'review');
assert.equal(calculateEconomics({}, {gas:0, transfer:0}).estimate, null);
assert.equal(calculateEconomics(source, {gas:138, transfer:0}).status, 'review');
assert.equal(calculateEconomics(source, {gas:137, transfer:0}).status, 'review');
assert.equal(calculateEconomics(source, {gas:137, transfer:0}, 0).status, 'profitable');
assert.equal(calculateEconomics(source, {gas:139, transfer:0}).status, 'unprofitable');
assert.equal(calculateEconomics({...source, revenue:100}).status, 'unprofitable');
const sorted = [
  {id:1,e:calculateEconomics({...source,revenue:100})},
  {id:2,e:calculateEconomics({...source,revenue:1000})},
  {id:3,e:calculateEconomics(source,{gas:0,transfer:0})},
].sort(compareOpportunities);
assert.deepEqual(sorted.map(row=>row.id), [3,2,1]);
console.log('Profit, loss, break-even, marginal, missing costs and sorting: PASS');
