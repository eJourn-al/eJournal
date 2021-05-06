<template>
    <div>
        <b-form-group
            :invalid-feedback="nameInvalidFeedback"
            :state="nameInputState"
        >
            <b-form-input
                v-model="criterion.name"
                placeholder="Name"
                type="text"
                trim
                required
            />
        </b-form-group>

        <b-form-group>
            <b-form-textarea
                v-model="criterion.description"
                placeholder="Optional description"
                rows="5"
            />
        </b-form-group>

        <b-form-group>
            <b-form-checkbox
                v-model="criterion.score_as_range"
                inline
                @change="scoreCriterionLevelsAsRange()"
            >
                Range
            </b-form-checkbox>

            <icon
                v-if="criterion.location != 0"
                class="trash-icon float-right"
                name="trash"
                @click.native="removeCriterion()"
            />
        </b-form-group>
    </div>
</template>

<script>
export default {
    props: {
        rubric: {
            required: true,
            type: Object,
        },
        criterion: {
            required: true,
            type: Object,
        },
    },
    data () {
        return {
            nameInvalidFeedback: null,
            nameInputState: null,
        }
    },
    computed: {
        maxPoints () {
            return Math.max(...this.criterion.levels.map((level) => level.points))
        },
    },
    watch: {
        'criterion.name': 'validateName',
    },
    methods: {
        removeCriterion () {
            this.rubric.criteria = this.rubric.criteria.filter((elem) => elem !== this.criterion)
            this.syncLocations(this.rubric.criteria)
        },
        scoreCriterionLevelsAsRange () {
            if (this.criterion.score_as_range) {
                const max = this.maxPoints

                let decrement
                if (this.criterion.levels.length <= 1) {
                    decrement = 0
                } else {
                    decrement = max / (this.criterion.levels.length - 1)
                }

                this.criterion.levels.forEach((level, i) => {
                    level.points = Math.round(((max - (decrement * i)) + Number.EPSILON) * 100) / 100

                    if (i === this.criterion.levels.length - 1 && this.criterion.levels.length !== 1) {
                        level.points = 0
                    }
                })
            }
        },
        syncLocations (arr) {
            arr.forEach((obj, i) => {
                obj.location = i
            })
        },
        validateName () {
            const name = this.criterion.name

            if (name === '') {
                this.nameInvalidFeedback = 'Name cannot be empty.'
                this.nameInputState = false
            } else if (this.rubric.criteria.some((elem) => elem.id !== this.criterion.id && elem.name === name)) {
                this.nameInvalidFeedback = 'Name is not unique.'
                this.nameInputState = false
            } else {
                this.nameInputState = null
            }
        },
    },
}
</script>

<style>

</style>
