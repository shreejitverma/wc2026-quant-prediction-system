import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  // api.types.ts is generated (npm run gen:api); never lint or hand-edit it.
  globalIgnores(["dist/**", "node_modules/**", "src/lib/api.types.ts"]),
  {
    files: ["**/*.{ts,tsx,mts}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      globals: { ...globals.browser },
    },
  },
  {
    files: ["**/*.tsx"],
    extends: [reactHooks.configs.flat.recommended],
  },
]);
