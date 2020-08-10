<template>
    <b-card
        :class="$root.getBorderClass(user.id)"
        class="no-hover"
    >
        <div class="d-flex">
            <div class="portrait-wrapper">
                <img
                    class="no-hover theme-img"
                    :src="user.profile_picture"
                />
            </div>
            <div class="student-details">
                <b class="max-one-line">
                    {{ user.full_name }}
                </b>
                <span class="max-one-line">
                    {{ user.username }}
                </span>
            </div>
        </div>
    </b-card>
</template>

<script>
export default {
    props: {
        user: {
            required: true,
        },
    },
}
</script>

<style lang="sass">
@import '~sass/partials/shadows.sass'
@import '~sass/modules/breakpoints.sass'

.portrait-wrapper
    position: relative
    min-width: 80px
    height: 70px
    img
        @extend .theme-shadow
        width: 70px
        height: 70px
        border-radius: 50% !important
    .number-badge
        position: absolute
        right: 0px
        top: 0px

.student-details
    position: relative
    width: calc(100% - 80px)
    min-height: 70px
    flex-direction: column
    padding: 10px
    &.list-view
        padding-left: 40px
    @include sm-max
        align-items: flex-end

</style>
