module.exports = {
    devServer: {
        // For gitpod, it needs to be disabled
        disableHostCheck: true,
        // The dev server sends no cache directives of its own, only a weak ETag,
        // so a browser is free to heuristically cache the bundle and never
        // revalidate. On desktop this is hidden by DevTools' "disable cache";
        // on a phone it shows up as "your fix didn't deploy" after every edit.
        headers: {
            'Cache-Control': 'no-store',
        },
    },
};
