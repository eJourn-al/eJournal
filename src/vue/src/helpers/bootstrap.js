/* eslint-disable */
// See https://github.com/bootstrap-vue/bootstrap-vue/blob/dev/src/components/index.js for all available options
import {
    BVConfigPlugin,
    AlertPlugin,
    // AspectPlugin,
    // AvatarPlugin,
    BadgePlugin,
    // BreadcrumbPlugin,
    ButtonPlugin,
    // ButtonGroupPlugin,
    // ButtonToolbarPlugin,
    // CalendarPlugin,
    CardPlugin,
    // CarouselPlugin,
    // CollapsePlugin,
    // DropdownPlugin,
    EmbedPlugin,
    FormPlugin,
    FormCheckboxPlugin,
    // FormDatepickerPlugin,
    FormFilePlugin,
    FormGroupPlugin,
    FormInputPlugin,
    // FormRadioPlugin,
    // FormRatingPlugin,
    FormSelectPlugin,
    // FormSpinbuttonPlugin,
    // FormTagsPlugin,
    FormTextareaPlugin,
    // FormTimepickerPlugin,
    // ImagePlugin,
    InputGroupPlugin,
    // JumbotronPlugin,
    LayoutPlugin,
    LinkPlugin,
    // ListGroupPlugin,
    // MediaPlugin,
    ModalPlugin,
    NavPlugin,
    NavbarPlugin,
    // OverlayPlugin,
    // PaginationPlugin,
    // PaginationNavPlugin,
    // PopoverPlugin,
    ProgressPlugin,
    // SidebarPlugin,
    // SpinnerPlugin,
    TablePlugin, // Table plugin includes TableLitePlugin and TableSimplePlugin
    TabsPlugin,
    // TimePlugin,
    // ToastPlugin,
    TooltipPlugin,
} from 'bootstrap-vue' /* "import 'bootstrap-vue'" directly will self register all components by default */

export default function initBootstrap (Vue) {
    Vue.use(BVConfigPlugin) // Should be first
    Vue.use(AlertPlugin)
    // Vue.use(AspectPlugin)
    // Vue.use(AvatarPlugin)
    Vue.use(BadgePlugin)
    // Vue.use(BreadcrumbPlugin)
    Vue.use(ButtonPlugin)
    // Vue.use(ButtonGroupPlugin)
    // Vue.use(ButtonToolbarPlugin)
    // Vue.use(CalendarPlugin)
    Vue.use(CardPlugin)
    // Vue.use(CarouselPlugin)
    // Vue.use(CollapsePlugin)
    // Vue.use(DropdownPlugin)
    Vue.use(EmbedPlugin)
    Vue.use(FormPlugin)
    Vue.use(FormCheckboxPlugin)
    // Vue.use(FormDatepickerPlugin)
    Vue.use(FormFilePlugin)
    Vue.use(FormGroupPlugin)
    Vue.use(FormInputPlugin)
    // Vue.use(FormRadioPlugin)
    // Vue.use(FormRatingPlugin)
    Vue.use(FormSelectPlugin)
    // Vue.use(FormSpinbuttonPlugin)
    // Vue.use(FormTagsPlugin)
    Vue.use(FormTextareaPlugin)
    // Vue.use(FormTimepickerPlugin)
    // Vue.use(ImagePlugin)
    Vue.use(InputGroupPlugin)
    // Vue.use(JumbotronPlugin)
    Vue.use(LayoutPlugin)
    Vue.use(LinkPlugin)
    // Vue.use(ListGroupPlugin)
    // Vue.use(MediaPlugin)
    Vue.use(ModalPlugin)
    Vue.use(NavPlugin)
    Vue.use(NavbarPlugin)
    // Vue.use(OverlayPlugin)
    // Vue.use(PaginationPlugin)
    // Vue.use(PaginationNavPlugin)
    // Vue.use(PopoverPlugin)
    Vue.use(ProgressPlugin)
    // Vue.use(SidebarPlugin)
    // Vue.use(SpinnerPlugin)
    Vue.use(TablePlugin)
    Vue.use(TabsPlugin)
    // Vue.use(TimePlugin)
    // Vue.use(ToastPlugin)
    Vue.use(TooltipPlugin)
}
