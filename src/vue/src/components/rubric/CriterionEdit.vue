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
            <b-button @click="scoreCriterionLevelsAsRange(criterion)">
                <icon
                    name="balance-scale"
                />
                Balance Score
            </b-button>

            <icon
                v-if="rubric.criteria.length > 1"
                class="trash-icon float-right"
                name="trash"
                @click.native="removeCriterion()"
            />
        </b-form-group>
    </div>
</template>

<script>
import genericUtitls from '@/utils/generic_utils.js'
import rubricUtils from '@/utils/rubric.js'

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
            scoreAsRange: false,
            scoreCriterionLevelsAsRange: rubricUtils.scoreCriterionLevelsAsRange,
        }
    },
    watch: {
        'criterion.name': 'validateName',
    },
    methods: {
        removeCriterion () {
            this.rubric.criteria = this.rubric.criteria.filter((elem) => elem !== this.criterion)
            genericUtitls.syncLocations(this.rubric.criteria)
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
