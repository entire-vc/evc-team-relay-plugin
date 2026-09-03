import tseslint from "typescript-eslint";
import globals from "globals";
export default tseslint.config(
  {
    languageOptions: {
      globals: { ...globals.browser },
      parserOptions: {
        projectService: { allowDefaultProject: ["eslint.config.js", "manifest.json"] },
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  ...tseslint.configs.recommendedTypeChecked,
  {
    rules: {
      "@typescript-eslint/no-unsafe-assignment": "error",
      "@typescript-eslint/no-unsafe-member-access": "error",
      "@typescript-eslint/no-unsafe-call": "error",
      "@typescript-eslint/no-unsafe-return": "error",
      "@typescript-eslint/no-unsafe-argument": "error",
      "@typescript-eslint/no-deprecated": "warn",
    },
  },
  {
    files: ["src/storage/y-indexeddb.js"],
    rules: {
      "@typescript-eslint/no-unsafe-assignment": "off",
      "@typescript-eslint/no-unsafe-argument": "off",
      "@typescript-eslint/no-unsafe-return": "off",
      "@typescript-eslint/no-unsafe-call": "off",
      // Vendored (adapted from y-indexeddb upstream) -- do not edit. It
      // subclasses lib0/observable's deprecated `Observable` and calls
      // `super()` from it, and stores bound methods on `this` before they're
      // assigned, which unbound-method can't distinguish from an unbound
      // callback reference. Neither is fixable without touching vendored
      // logic.
      "@typescript-eslint/unbound-method": "off",
      "@typescript-eslint/no-deprecated": "off",
    },
  },
  {
    // Vendored/adapted-from-upstream (y-sweet / yjs provider) -- do not edit.
    // Subclasses lib0/observable's `Observable`, which is marked
    // `@deprecated` upstream in favor of `ObservableV2`; the class and its
    // `super()` calls are the vendored contract, not something this plugin
    // can migrate off unilaterally.
    files: ["src/client/provider.ts"],
    rules: {
      "@typescript-eslint/no-deprecated": "off",
    },
  },
  { ignores: ["node_modules/", "main.js", "*.config.mjs"] }
);
