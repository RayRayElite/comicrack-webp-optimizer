// Exercise the local HTML's script without a browser or external dependencies.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.join(__dirname, 'Test Environment', 'Quality Lab');
const runs = fs.readdirSync(root).sort();
const html = fs.readFileSync(path.join(root, runs.at(-1), 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
  constructor(id) { this.id = id; this.children = []; this.selectedIndex = 0; this.rawValue = ''; }
  add(option) { this.children.push(option); }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  set value(value) {
    this.rawValue = String(value);
    const index = this.children.findIndex(o => String(o.value) === String(value));
    if (index >= 0) this.selectedIndex = index;
  }
  get value() { return this.children[this.selectedIndex]?.value ?? this.rawValue; }
  click() { this.clicked = true; }
}
const elements = {};
let exported;
const context = {
  document: {getElementById: id => elements[id] ||= new Element(id), createElement: id => new Element(id)},
  Option: function(text, value) { this.text = text; this.value = String(value); },
  localStorage: {getItem: () => null, setItem: () => {}},
  URL: {createObjectURL: blob => { exported = blob; return 'blob:test'; }, revokeObjectURL: () => {}},
  Blob, setTimeout: () => {}, requestAnimationFrame: callback => callback(),
};
vm.createContext(context);
vm.runInContext(script, context);
assert.equal(elements.page.children.length, 9);
assert.equal(elements.quality.value, '80');
assert.equal(elements.rows.children.length, 10);
assert.match(elements.after.textContent, /reduction/);
elements.rating.value = 'Indistinguishable';
elements.rating.onchange();
assert.match(elements.status.textContent, /saved/);
elements.next.onclick();
assert.equal(elements.page.selectedIndex, 1);
assert.equal(elements.rating.value, '');
elements.previous.onclick();
assert.equal(elements.rating.value, 'Indistinguishable');
elements.zoom.value = 'actual'; elements.zoom.onchange();
assert.equal(elements.left.className, 'viewport actual');
elements.left.scrollTop = 100; elements.left.scrollLeft = 40; elements.left.onscroll();
assert.equal(elements.right.scrollTop, 100);
assert.equal(elements.right.scrollLeft, 40);
elements.export.onclick();
exported.text().then(text => {
  const result = JSON.parse(text);
  assert.equal(result.ratings.length, 1);
  assert.equal(result.ratings[0].quality, 80);
  assert.equal(result.ratings[0].rating, 'Indistinguishable');
  console.log('PASS: all quality levels, page navigation, rating persistence, zoom, matched scrolling and JSON export');
});
