module.exports = {
    extends: ['eslint:recommended', 'plugin:vue/recommended'],
    rules: {
        'vue/no-unused-vars': 'error',
        'vue/html-indent': ['error', 4, { alignAttributesVertically: false }],
        'vue/max-attributes-per-line': 0,
        'vue/attribute-hyphenation': ['error', 'never'],
        'vue/singleline-html-element-content-newline': 'off',
        'no-case-declarations': 'off',
        'no-unused-vars': 'off',
        quotes: ['error', 'single'],
    },
    env: {
        node: true,
    },
    parserOptions: {
        parser: '@typescript-eslint/parser',
    },
};
