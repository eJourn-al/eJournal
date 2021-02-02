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

    assignmentWithDatesDisplay (assignment) {
        let display = assignment.name

        if (!assignment.unlock_date && !assignment.due_date && !assignment.lock_date) {
            return display
        }

        display += ' ('

        if (assignment.unlock_date) {
            display += `${assignment.unlock_date.substring(0, 4)}`
        }

        if (assignment.unlock_date && (assignment.due_date || assignment.lock_date)) {
            display += ' - '
        }

        if (assignment.due_date) {
            display += `${assignment.due_date.substring(0, 4)}`
        } else if (assignment.lock_date) {
            display += `${assignment.lock_date.substring(0, 4)}`
        }

        display += ')'

        return display
    },

    parseYouTubeVideoID (url) {
        const re = /^((?:https?:)?\/\/)?((?:www|m)\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/|.+\?v=)?(?<id>[A-Za-z0-9=_-]{11})/ // eslint-disable-line
        const match = url.match(re)

        return (match && match.groups.id) ? match.groups.id : false
    },
}
