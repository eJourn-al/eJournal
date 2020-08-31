export default {
    /* Converts an arraybuffer response to a humanreadable text. */
    parseArrayBuffer (arrayBuffer) {
        if (arrayBuffer instanceof ArrayBuffer) {
            const enc = new TextDecoder('utf-8')

            return JSON.parse(enc.decode(arrayBuffer))
        }
        return arrayBuffer
    },

    invalidAccessToken (error) {
        if (error) {
            let code
            if (error.response.data instanceof ArrayBuffer) {
                code = this.parseArrayBuffer(error.response.data).code
            } else {
                code = error.response.data.code
            }

            return code === 'token_not_valid'
        } else {
            return false
        }
    },

    courseWithDatesDisplay (course) {
        let display = course.name

        if (course.startdate || course.enddate) {
            display += ` (${course.startdate ? course.startdate.substring(0, 4) : ''} - ${
                course.enddate ? course.enddate.substring(0, 4) : ''})`
        }

        return display
    },
}
