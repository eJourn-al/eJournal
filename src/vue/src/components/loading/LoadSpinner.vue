<template>
    <b-card class="large-load-spinner">
        <img
            src="/ejournal-book.svg"
            class="theme-img"
        />
        <img
            src="/ejournal-book.svg"
            class="theme-img"
        />
    </b-card>
</template>

<style lang="sass">
@import '~sass/modules/keyframe-prefixes.sass'

.card.large-load-spinner
    position: relative
    left: 50%
    transform: translateX(-50%)
    width: 100px
    height: 100px
    overflow: hidden
    img
        position: absolute
        width: 56px
        animation: 2.5s ease infinite slide-resize
        &:nth-child(1)
            animation-delay: 1.25s
            -webkit-animation-delay: 1.25s
            left: 122px
    +keyframes(slide-resize)
        0%
            left: 122px
            transform: scale(0.4)
        50%
            left: 22px
            transform: scale(1)
        100%
            left: -78px
            transform: scale(0.4)
</style>
