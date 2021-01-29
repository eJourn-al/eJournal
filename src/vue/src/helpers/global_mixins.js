export default function initGlobalMixins (Vue) {
    Vue.mixin({
        methods: {
            validateData () {
                const invalid = Object.entries(this._data).some((entry) => {
                    const [key, value] = entry

                    if (key.includes('State') && value === false) {
                        const invalidFeedback = this._data[key.replace('InputState', 'InvalidFeedback')]
                        this.$toasted.error(invalidFeedback)
                        return true
                    }
                    return false
                })

                return !invalid
            },
        },
    })
}
