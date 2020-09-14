const path = require('path')
const webpack = require('webpack') // eslint-disable-line import/no-extraneous-dependencies
const currentRelease = require('./build/current-release')
const supportedBrowsers = require('./build/supported-browsers')
const SentryWebpackPlugin = require('@sentry/webpack-plugin')

module.exports = {
    configureWebpack: {
        resolve: {
            alias: {
                '@': path.resolve(__dirname, './src'),
                sass: path.resolve(__dirname, './src/sass'),
                public: path.resolve(__dirname, './public'),
            },
        },
        plugins: [
            new webpack.DefinePlugin({
                CurrentRelease: JSON.stringify(currentRelease),
                SupportedBrowsers: JSON.stringify(supportedBrowsers),
                CustomEnv: {
                    API_URL: JSON.stringify(process.env.API_URL),
                    SENTRY_URL: JSON.stringify(process.env.SENTRY_URL),
                    SENTRY_DSN: JSON.stringify(process.env.SENTRY_DSN),
                    SENTRY_ORG: JSON.stringify(process.env.SENTRY_ORG),
                    SENTRY_PROJECT: JSON.stringify(process.env.SENTRY_PROJECT),
                    CODE_VERSION: JSON.stringify(process.env.CODE_VERSION),
                },
            }),
            new webpack.ProvidePlugin({
                introJs: ['intro.js'],
            }),
        ].concat(process.env.NODE_ENV === 'production' ?
            new SentryWebpackPlugin({
                include: './dist',
                ignore: ['node_modules', 'webpack.config.js'],
                release: process.env.RELEASE_VERSION,
            })
            : []
        ),
    },
}
