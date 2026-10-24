/* No npm dependencies: exercise the production enhancement with native-label semantics. */
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../docs/javascripts/navigation-accessibility.js'), 'utf8');

function fixture(checked = false) {
  const listeners = {};
  const attrs = {};
  const panel = { tagName: 'NAV', id: '', attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } };
  const toggle = { id: '__nav_3', checked, addEventListener(k, fn) { listeners[k] = fn; } };
  const link = { textContent: ' Information ', click() { throw Error('Disclosure must not navigate'); } };
  const control = {
    htmlFor: toggle.id, attrs, clicks: 0, listeners: {},
    parentElement: { querySelector() { return link; }, nextElementSibling: panel },
    setAttribute(k, v) { attrs[k] = v; },
    addEventListener(k, fn) { this.listeners[k] = fn; },
    click() { this.clicks++; toggle.checked = !toggle.checked; listeners.change(); },
  };
  const document = {
    readyState: 'complete', querySelectorAll() { return [control]; },
    getElementById(id) { return id === toggle.id ? toggle : null; },
  };
  vm.runInNewContext(source, { document });
  return { control, toggle, panel, listeners };
}
function key(control, type, value, repeat = false) {
  const event = { type, key: value, repeat, prevented: false, stopped: false,
    preventDefault() { this.prevented = true; },
    stopImmediatePropagation() { this.stopped = true; },
  };
  control.listeners[type](event);
  return event;
}

test('native section controls receive names, roles and associated expanded state', () => {
  for (const checked of [false, true]) {
    const { control, panel } = fixture(checked);
    assert.equal(control.attrs.role, 'button');
    assert.equal(control.attrs['aria-controls'], panel.id);
    assert.equal(control.attrs['aria-expanded'], String(checked));
    assert.equal(control.attrs['aria-label'], `${checked ? 'Collapse' : 'Expand'} Information`);
    assert.equal(panel.attrs['aria-expanded'], String(checked));
    assert.equal(panel.attrs['aria-labelledby'], '__nav_3_index');
  }
});
test('Enter and Space toggle once without following the title link', () => {
  const { control, toggle } = fixture();
  for (const value of ['Enter', ' ']) {
    const before = toggle.checked;
    const down = key(control, 'keydown', value);
    assert.equal(toggle.checked, !before);
    assert.equal(down.prevented, true);
    assert.equal(down.stopped, true);
    key(control, 'keydown', value, true);
    key(control, 'keyup', value);
    assert.equal(toggle.checked, !before);
    assert.equal(control.attrs['aria-expanded'], String(!before));
  }
  assert.equal(control.clicks, 2);
  assert.equal(key(control, 'keydown', 'Tab').prevented, false);
});
test('pointer/native checkbox changes update the control and panel together', () => {
  const { control, toggle, panel, listeners } = fixture();
  control.click();
  assert.equal(control.attrs['aria-label'], 'Collapse Information');
  toggle.checked = false;
  listeners.change();
  assert.equal(control.attrs['aria-label'], 'Expand Information');
  assert.equal(panel.attrs['aria-expanded'], 'false');
});
