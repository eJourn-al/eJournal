export default function initGlobalMixins (Vue) {
    Vue.mixin({
        methods: {
            /* Validates the components data making use of the following naming scheme:
             *
             * For each different validated input:
             *
             * - <input>InputState, false indicating the input failed validation
             * - <input>InvalidFeedback, containing the string providing the failed validation message
             * - r'validate.*Input', method used to validate the relevant input state, and is responsible for setting
             *      the corresponding InputState and InvalidFeedback message.
             *
             * Each method which satisfies the pattern is called, which should set their respective input states.
             * If any state is false, return false else true.
             *
             * Will toast the invalid feedback of the first invalid state
             */
            validateData () {
                Object.entries(this).forEach((obj) => {
                    const [key, value] = obj

                    if (key.startsWith('validate') && key.endsWith('Input') && typeof value === 'function') {
                        value()
                    }
                })

                const invalid = Object.entries(this._data).some((entry) => {
                    const [key, value] = entry

                    if (key.includes('InputState') && value === false) {
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
