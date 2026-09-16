require('../../engine/node_modules/ts-node').register({
    transpileOnly: true,
    compiler: require.resolve('typescript'),
    compilerOptions: { module: 'CommonJS', moduleResolution: 'Node', target: 'ES2022', importHelpers: false },
});
const { lessons } = require('../src/tutorial/lessons');
console.log(
    JSON.stringify(
        { chapters: lessons.map(({ id, version, title, description }) => ({ id, version, title, description })) },
        null,
        2
    )
);
