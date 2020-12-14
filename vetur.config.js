/** @type {import('vls').VeturConfig} */
module.exports = {
  settings: {
    "vetur.useWorkspaceDependencies": true,
    "vetur.experimental.templateInterpolationService": false // Not very usable withouto typescript
  },
  projects: [
    {
      /* Project location relative to `vetur.config.js`. */
      root: './src/vue',
      /* **optional** default: `'package.json'`
       * Where is package.json located relative to the root property */
      package: './package.json',
    }
  ]
}
