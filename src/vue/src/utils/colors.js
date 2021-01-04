export default {
    /**
     * Code based on https://github.com/o-klp/hsl_rgb_converter
     * Converts an HSL color value to RGB. Conversion formula
     * adapted from http://en.wikipedia.org/wiki/HSL_and_HSV#Converting_to_RGB.
     * Assumes h is contained in the set [0, 360) and s, and l are contained in the set [0, 1].
     * Returns r, g, and b in the set [0, 255].
     *
     * @param   {number}  hue            The hue
     * @param   {number}  saturation     The saturation
     * @param   {number}  lightness      The lightness
     * @return  {Array}                  The RGB representation
     */
    hslToRgb (hue, saturation, lightness) {
        if (hue >= 360) { hue = 360 - 0.0001 } // eslint-disable-line

        if (hue === undefined) {
            return [0, 0, 0]
        }

        const chroma = (1 - Math.abs((2 * lightness) - 1)) * saturation
        let huePrime = hue / 60
        const secondComponent = chroma * (1 - Math.abs((huePrime % 2) - 1))

        huePrime = Math.floor(huePrime)
        let red
        let green
        let blue

        if (huePrime === 0) {
            red = chroma
            green = secondComponent
            blue = 0
        } else if (huePrime === 1) {
            red = secondComponent
            green = chroma
            blue = 0
        } else if (huePrime === 2) {
            red = 0
            green = chroma
            blue = secondComponent
        } else if (huePrime === 3) {
            red = 0
            green = secondComponent
            blue = chroma
        } else if (huePrime === 4) {
            red = secondComponent
            green = 0
            blue = chroma
        } else if (huePrime === 5) {
            red = chroma
            green = 0
            blue = secondComponent
        }

        const lightnessAdjustment = lightness - (chroma / 2)
        red += lightnessAdjustment
        green += lightnessAdjustment
        blue += lightnessAdjustment

        red = Math.min(Math.floor(red * 256), 255)
        green = Math.min(Math.floor(green * 256), 255)
        blue = Math.min(Math.floor(blue * 256), 255)

        return { red, green, blue }
    },

    randomBrightHSLColor () {
        const hue = Math.random()

        const saturationFloor = 0.8
        const saturation = Math.random() * (1 - saturationFloor) + saturationFloor

        const lightnessFloor = 0.4
        const lighnessCeil = 0.8
        const lightness = (Math.random() * (1 - lightnessFloor) + lightnessFloor) - (1 - lighnessCeil)

        return { hue, saturation, lightness }
    },

    componentToHex (c) {
        const hex = c.toString(16)
        return hex.length === 1 ? `0${hex}` : hex
    },

    rgbToHex (r, g, b) {
        return `#${this.componentToHex(r)}${this.componentToHex(g)}${this.componentToHex(b)}`
    },

    randomBrightRGBcolor () {
        const hsl = this.randomBrightHSLColor()
        const rgb = this.hslToRgb(hsl.hue * 360, hsl.saturation, hsl.lightness)
        return this.rgbToHex(rgb.red, rgb.green, rgb.blue)
    },
}
