// jsdom has no layout engine, so it omits the scrolling APIs entirely rather
// than making them no-ops. Any component that scrolls something into view
// therefore throws under test — and because the call is deferred by a timer,
// whether it throws depends on how long the test happens to run, which made it
// a flake that only surfaced on slower CI machines.
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {}
}
