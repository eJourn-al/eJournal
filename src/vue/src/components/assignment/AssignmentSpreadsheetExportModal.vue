<template>
    <b-modal
        ref="assignmentExportSpreadsheetModal"
        title="Export results to spreadsheet"
        size="lg"
        noEnforceFocus
    >
        Select which columns should be included in the exported file.
        <b-form-checkbox
            v-model="exportSelection.name"
            class="mt-1"
        >
            Journal name
            <tooltip
                class="ml-1"
                tip="Custom for group journals, author name for individual journals"
            />
        </b-form-checkbox>
        <b-form-checkbox v-model="exportSelection.full_name">
            Full name(s)
            <tooltip
                class="ml-1"
                tip="If a journal has multiple authors, names will be combined"
            />
        </b-form-checkbox>
        <b-form-checkbox v-model="exportSelection.username">
            Username(s)
            <tooltip
                class="ml-1"
                tip="If a journal has multiple authors, usernames will be combined"
            />
        </b-form-checkbox>
        <b-form-checkbox v-model="exportSelection.total_points">
            Total points
            <tooltip
                class="ml-1"
                tip="Total number of points given for a journal"
            />
        </b-form-checkbox>
        <b-form-checkbox v-model="exportSelection.progress_percentage">
            Progress percentage
            <tooltip
                class="ml-1"
                tip="Total number of points as percentage of the maximum possible points configured for the assignment"
            />
        </b-form-checkbox>
        <b-form-checkbox v-model="exportSelection.entry_points">
            Entry points
            <tooltip
                class="ml-1"
                tip="Total number of points given for all entries in a journal"
            />
        </b-form-checkbox>
        <b-form-checkbox
            v-model="exportSelection.bonus_points"
            class="mb-2"
        >
            Bonus points
            <tooltip
                class="ml-1"
                tip="Number of bonus points given for a journal"
            />
        </b-form-checkbox>
        <template #modal-footer>
            <b-button
                v-if="exportFilteredResults"
                class="mr-auto"
                @click="exportFilteredResults = false"
            >
                <icon name="filter"/>
                Current filter only
            </b-button>
            <b-button
                v-else
                class="mr-auto"
                @click="exportFilteredResults = true"
            >
                <icon name="book"/>
                All journals
            </b-button>
            <b-button
                class="green-button float-right"
                :class="{ 'input-disabled': exportInProgress || !someExportOptionSelected }"
                @click="exportAssignmentSpreadsheet()"
            >
                <icon name="file-export"/>
                Export Results
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import ExcelJS from 'exceljs'
import FileSaver from 'file-saver/src/FileSaver.js'
import tooltip from '@/components/assets/Tooltip.vue'

export default {
    components: {
        tooltip,
    },
    props: {
        assignment: {
            required: true,
        },
        assignmentJournals: {
            required: true,
        },
        filteredJournals: {
            required: true,
        },
    },
    data () {
        return {
            exportSelection: {
                name: true,
                full_name: false,
                username: true,
                progress_percentage: false,
                total_points: true,
                entry_points: false,
                bonus_points: false,
            },
            exportInProgress: false,
            exportFilteredResults: true,
        }
    },
    computed: {
        someExportOptionSelected () {
            return Object.values(this.exportSelection).some((bool) => bool)
        },
    },
    methods: {
        exportExcel (name, data) {
            // Create a new workbook.
            const workbook = new ExcelJS.Workbook()

            // Specify metadata / source.
            workbook.creator = 'eJournal'
            workbook.created = new Date()
            workbook.properties.date1904 = true

            // Create a new worksheet with the first row frozen (for headers).
            const sheet = workbook.addWorksheet(name, { views: [{ state: 'frozen', ySplit: 1 }] })

            // Fill the sheet columns with each property of the data object as a column.
            // The header of the column is the property name. Column indices start at 1.
            Object.keys(data).forEach((header, key) => {
                const beautifiedHeader = header.charAt(0).toUpperCase() + header.substring(1).replace('_', ' ')
                sheet.getColumn(key + 1).values = [beautifiedHeader].concat(data[header])
            })

            // Write the spreadsheet to a buffer, then
            return workbook.xlsx.writeBuffer(name)
                .then((spreadsheetBuffer) => {
                    FileSaver.saveAs(new Blob([spreadsheetBuffer],
                        { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }),
                    `${name}.xlsx`)
                })
        },
        exportAssignmentSpreadsheet () {
            const journalsToExport = this.exportFilteredResults ? this.filteredJournals : this.assignmentJournals
            const data = {}

            this.exportInProgress = true

            if (this.exportSelection.name) {
                data.name = journalsToExport.map((journal) => journal.name)
            }
            if (this.exportSelection.full_name) {
                data.full_name = journalsToExport.map((journal) => journal.full_names)
            }
            if (this.exportSelection.username) {
                data.username = journalsToExport.map((journal) => journal.usernames)
            }
            if (this.exportSelection.progress_percentage) {
                data.progress_percentage = journalsToExport.map(
                    (journal) => this.zeroIfNull((journal.grade * 100) / this.assignment.points_possible).toFixed(0))
            }
            if (this.exportSelection.total_points) {
                data.total_points = journalsToExport.map((journal) => journal.grade)
            }
            if (this.exportSelection.entry_points) {
                data.entry_points = journalsToExport.map(
                    (journal) => (journal.grade - journal.bonus_points))
            }
            if (this.exportSelection.bonus_points) {
                data.bonus_points = journalsToExport.map((journal) => journal.bonus_points)
            }

            this.exportExcel(`eJournal export ${this.assignment.name}`, data)
                .then(() => {
                    this.exportInProgress = false
                    this.$emit('spreadsheet-exported')
                    this.$toasted.success('Successfully exported results to spreadsheet.')
                })
                .catch(() => {
                    this.exportInProgress = false
                    this.$toasted.error('Something went wrong while exporting the spreadsheet.')
                })
        },
        zeroIfNull (val) {
            return (val === null) ? 0 : val
        },
        show () {
            this.$refs.assignmentExportSpreadsheetModal.show()
        },
        hide () {
            this.$refs.assignmentExportSpreadsheetModal.hide()
        },
    },
}
</script>
