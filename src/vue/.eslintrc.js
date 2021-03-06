module.exports = {
    root: true,
    parserOptions: {
        parser: 'babel-eslint'
    },
    env: {
        browser: true,
        es6: true,
        node: true
    },
    extends: [
        'plugin:vue/recommended',
        'airbnb-base',
    ],
    plugins: [
        'vue',
        'sort-imports-es6-autofix',
    ],
    rules: {
        'arrow-parens': ['error', 'always'],
        'generator-star-spacing': 'off',
        'import/no-cycle': 'off',
        'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
        'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
        'semi': 0, // do not require ;
        'indent': ['error', 4],
        'vue/component-name-in-template-casing': ['error', 'kebab-case', {
            'registeredComponentsOnly': false,
            'ignores': []
        }],
        'vue/html-closing-bracket-spacing': ['error', {
            'startTag': 'never',
            'endTag': 'never',
            'selfClosingTag': 'never',
        }],
        'vue/html-closing-bracket-newline': ['error', {
            'singleline': 'never',
            'multiline': 'always',
        }],
        'vue/html-self-closing': ['error', {
            'html': {
                'void': 'always',
                'normal': 'always',
                'component': 'always'
            },
            'svg': 'always',
            'math': 'always'
        }],
        'vue/html-indent': ['error', 4],
        'vue/require-prop-types': 'off', // Do not demand component property types
        'vue/script-indent': 'off', // clash with base eslint for some edge cases
        'vue/attribute-hyphenation': 'off',
        'import/extensions': ['error', 'ignorePackages'],
        'space-before-function-paren': ['error', 'always'],
        'max-len': ['error', { 'code': 120 }],
        'prefer-destructuring': 'off',
        'no-param-reassign': ['error', { 'props': false }], // vuex
        'no-else-return': 'off',
        'no-underscore-dangle': 'off',
        'no-plusplus': 'off',
        'no-alert': 'off', // allow alerts (we should create a custom component for this)
        'function-paren-newline': 'off',
        'complexity': ['error', { 'max': 26 }],
        'max-lines-per-function': ['error', { 'max': 121 }],
        'import/order': 'off',  // conflicts with sort-imports
        'sort-imports-es6-autofix/sort-imports-es6': [2, {
            'ignoreCase': false,
            'ignoreMemberSort': false,
            'memberSyntaxSortOrder': ['none', 'all', 'multiple', 'single']
        }],
        'object-curly-newline': ['error', {
            'ObjectExpression': { 'consistent': true, 'minProperties': 5 },
        }],
    },
    settings: {
        'import/resolver': {
            webpack: {
                config: require.resolve('@vue/cli-service/webpack.config.js')
            },
        },
    },
    globals: {
        CurrentRelease: true,
        CustomEnv: true,
    },
}
