export default {
    scoreCriterionLevelsAsRange (criterion) {
        const max = Math.max(...this.criterion.levels.map((level) => level.points))

        let decrement
        if (criterion.levels.length <= 1) {
            decrement = 0
        } else {
            decrement = max / (criterion.levels.length - 1)
        }

        criterion.levels.forEach((level, i) => {
            level.points = Math.round(((max - (decrement * i)) + Number.EPSILON) * 100) / 100

            if (i === criterion.levels.length - 1 && criterion.levels.length !== 1) {
                level.points = 0
            }
        })
    },
}
