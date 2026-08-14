module.exports = {
    root: true,
    env: {
        node: true,
    },
    parserOptions: {
        ecmaVersion: 2020,
    },
    parser: '@typescript-eslint/parser',
    plugins: ['@typescript-eslint'],
    extends: [
        'eslint:recommended',
        'plugin:@typescript-eslint/eslint-recommended',
        'plugin:@typescript-eslint/recommended',
    ],
    rules: {
        'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
        'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
        semi: ['error', 'always'],
        '@typescript-eslint/no-non-null-assertion': 'off',
        //    '@typescript-eslint/consistent-type-assertions': 'off',
        //    '@typescript-eslint/no-explicit-any': 'off',
        '@typescript-eslint/no-empty-function': 'off',
        '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
        '@typescript-eslint/explicit-function-return-type': 'off',
        '@typescript-eslint/no-use-before-define': 'off',
        '@typescript-eslint/no-namespace': 'off',
        'no-inner-declarations': 'off',
        'no-return-assign': 'off',
        //    'no-fallthrough': 'off',
        'no-empty': 'off',
        // avoidEscape lets a string that itself contains an apostrophe use double
        // quotes ("Xi'an") instead of escaping ('Xi\'an'). Without it this rule and
        // Prettier deadlock: Prettier rewrites the escaped form to double quotes to
        // minimise escapes, and the rule then rejects what Prettier just produced.
        quotes: ['error', 'single', { avoidEscape: true }],
    },
};
