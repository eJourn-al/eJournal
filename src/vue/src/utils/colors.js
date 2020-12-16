export default {
    /* eslint-disable */
    /**
     * Converts an HSL color value to RGB. Conversion formula
     * adapted from http://en.wikipedia.org/wiki/HSL_color_space.
     * Assumes h, s, and l are contained in the set [0, 1] and
     * returns r, g, and b in the set [0, 255].
     *
     * Taken from: https://stackoverflow.com/a/9493060
     *
     * @param   {number}  h       The hue
     * @param   {number}  s       The saturation
     * @param   {number}  l       The lightness
     * @return  {Array}           The RGB representation
     */
    hslToRgb (h, s, l) {
        let r, g, b

        if (s == 0) {
            r = g = b = l; // achromatic
        } else {
            var hue2rgb = function hue2rgb(p, q, t) {
                if(t < 0) t += 1;
                if(t > 1) t -= 1;
                if(t < 1/6) return p + (q - p) * 6 * t;
                if(t < 1/2) return q;
                if(t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                return p;
            }

            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }

        r = Math.min(Math.floor(r * 256), 255)
        g = Math.min(Math.floor(g * 256), 255)
        b = Math.min(Math.floor(b * 256), 255)

        return {red: r, green: g, blue: b}
    },
    /* eslint-enable */

    randomBrightHSLColor () {
        const hue = Math.random()

        const saturationFloor = 0.8
        const saturation = Math.random() * (1 - saturationFloor) + saturationFloor

        const lightnessFloor = 0.4
        const lightness = Math.random() * (1 - lightnessFloor) + lightnessFloor

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
        const rgb = this.hslToRgb(hsl.hue, hsl.saturation, hsl.lightness)
        return this.rgbToHex(rgb.red, rgb.green, rgb.blue)
    },
}
