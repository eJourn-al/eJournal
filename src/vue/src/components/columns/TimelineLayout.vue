<template>
    <b-row noGutters>
        <b-col
            md="12"
            lg="8"
            xl="9"
            class="combined-content-timeline-page"
        >
            <b-row noGutters>
                <b-col
                    md="12"
                    xl="4"
                    class="left-content-timeline-page"
                >
                    <slot name="left"/>
                </b-col>

                <b-col
                    md="12"
                    xl="8"
                    class="main-content-timeline-page"
                >
                    <slot name="center"/>
                </b-col>
            </b-row>
        </b-col>

        <b-col
            md="12"
            lg="4"
            xl="3"
            class="right-content-timeline-page right-content"
        >
            <slot name="right"/>
        </b-col>

        <slot/>
    </b-row>
</template>

<script>
export default {
    name: 'TimelineLayout',
}
</script>

<style lang="sass">
@import '~sass/partials/timeline-page-layout.sass'
</style>
