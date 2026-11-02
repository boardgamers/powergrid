module.exports = {
    // Webpack 4 cannot parse these forms even when modern browsers support them.
    presets: [
        [
            '@vue/cli-plugin-babel/preset',
            {
                include: ['@babel/plugin-transform-numeric-separator', '@babel/plugin-transform-export-namespace-from'],
            },
        ],
    ],
};
