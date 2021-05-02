const path = require('path')
const webpack = require('webpack') // eslint-disable-line import/no-extraneous-dependencies
const currentRelease = require('./build/current-release')
const SentryWebpackPlugin = require('@sentry/webpack-plugin')

const CHUNKS_WHICH_SHOULD_NOT_BE_PREFETCHED = [
    'exceljs',
    'pdf',
    'sortable',
    'draggable',
    'croppa',
    'intro',
]

module.exports = {
    chainWebpack: (config) => {
        if (config.plugins.has('prefetch')) {
            config.plugin('prefetch').tap((options) => {
                options[0].fileBlacklist = options[0].fileBlacklist || []

                options[0].fileBlacklist.push(/.+?\.map$/)
                CHUNKS_WHICH_SHOULD_NOT_BE_PREFETCHED.forEach((chunkName) => {
                    options[0].fileBlacklist.push(new RegExp(`.*${chunkName}.+?\.js$`))
                })

                return options
            })
        }

        if (config.plugins.has('optimize-css')) {
            config.plugins.delete('optimize-css')
        }
    },
    configureWebpack: {
        /* Splits all vendors into dedicated chunks */
        optimization: {
            runtimeChunk: 'single',
            splitChunks: {
                chunks: 'all',
                maxInitialRequests: Infinity,
                minSize: 0,
                cacheGroups: {
                    vendor: {
                        test: /[\\/]node_modules[\\/]/,
                        name (module) {
                            /* Get the name, e.g. node_modules/packageName/not/this.js or node_modules/packageName */
                            const packageName = module.context.match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/)[1]

                            /* NPM package names are URL-safe, but some servers don't like @ symbols */
                            return `npm.${packageName.replace('@', '')}`
                        },
                    },
                },
            },
        },
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
        ].concat(process.env.NODE_ENV === 'production'
            ? new SentryWebpackPlugin({
                include: './dist',
                ignore: ['node_modules', 'webpack.config.js'],
                release: process.env.RELEASE_VERSION,
            })
            : [],
        ),
    },

    css: {
        loaderOptions: {
            sass: {
                prependData: `
                    @import "~sass/modules/colors.sass"
                    @import "~sass/modules/breakpoints.sass"
                    @import "~sass/modules/dimensions.sass"
                `,
            },
        },
    },
}
