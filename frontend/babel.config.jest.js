// Jest-only Babel config. Intentionally NOT named babel.config.js so Next.js
// (Turbopack/SWC) does not pick it up and disable the automatic JSX runtime.
module.exports = {
  presets: [
    ["@babel/preset-env", { targets: { node: "current" } }],
    ["@babel/preset-react", { runtime: "automatic" }],
    "@babel/preset-typescript",
  ],
};
