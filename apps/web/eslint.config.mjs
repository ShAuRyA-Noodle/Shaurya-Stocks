import nextConfig from "eslint-config-next"
import tseslint from "typescript-eslint"

const config = [
  ...nextConfig,
  {
    ignores: [".next/**", "node_modules/**"],
  },
  {
    files: ["**/*.ts", "**/*.tsx"],
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
]

export default config
