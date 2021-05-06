<template>
    <div class="level-container">
        <div class="level-main-content">
            <b-form-group>
                <b-form-input
                    v-model="level.name"
                    placeholder="Name"
                    type="text"
                    trim
                    required
                />
            </b-form-group>

            <b-form-group>
                <b-form-textarea
                    v-model="level.description"
                    placeholder="Optional description"
                    type="text"
                    trim
                    rows="5"
                />
            </b-form-group>

            <b-form-input
                v-model="level.points"
                class="inline"
                type="number"
                size="2"
                placeholder="-"
                min="0.0"
                :disabled="criterion.score_as_range"
                :formatter="floatFormatter"
            />

            <icon
                v-if="!(firstLevel || lastLevel)"
                class="trash-icon float-right mt-3"
                name="trash"
                @click.native="removeLevel()"
            />
        </div>

        <div
            v-if="!lastLevel"
            class="add-level"
        >
            <icon
                class="validate-icon"
                name="plus"
                @click.native="addLevel()"
            />
        </div>
    </div>
</template>

<script>
export default {
    props: {
        level: {
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
            newCriterionId: -1,
        }
    },
    computed: {
        firstLevel () { return this.level.location === 0 },
        lastLevel () { return this.level.location === this.criterion.levels.length - 1 },
    },
    methods: {
        /* Adds a level after (to the right of) the current level */
        addLevel () {
            const afterLevel = this.level

            this.criterion.levels.splice(afterLevel.location + 1, 0, {
                name: `Less than ${afterLevel.name}`,
                description: '',
                points: afterLevel.points,
                location: afterLevel.location + 1,
                id: this.newCriterionId--,
            })

            this.syncLocations(this.criterion.levels)
        },
        removeLevel () {
            this.criterion.levels = this.criterion.levels.filter((elem) => elem !== this.level)
            this.syncLocations(this.criterion.levels)
        },
        syncLocations (arr) {
            arr.forEach((obj, i) => {
                obj.location = i
            })
        },
        floatFormatter (value) {
            if (value === '') { return 0 }
            return parseFloat(value)
        },
    },
}
</script>
