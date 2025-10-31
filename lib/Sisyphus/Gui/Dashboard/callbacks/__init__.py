from .callbacks_conditions  import register_callbacks as register_conditions_callbacks
from .callbacks_filter      import register_callbacks as register_filter_callbacks
from .callbacks_valuefilter import register_callbacks as register_valuefilter_callbacks
from .callbacks_hidecharts  import register_callbacks as register_hidecharts_callbacks
from .callbacks_load        import register_callbacks as register_load_callbacks
from .callbacks_plot        import register_callbacks as register_plot_callbacks
#from .callbacks_switch      import register_callbacks as register_switch_callbacks
from .callbacks_sync        import register_callbacks as register_sync_callbacks
from .callbacks_updatemenu  import register_callbacks as register_updatemenu_callbacks
#from .callbacks_jsonselect  import register_callbacks as register_jsonselect_callbacks


__all__ = [
    "register_conditions_callbacks",
    "register_filter_callbacks",
    "register_valuefilter_callbacks",
    "register_hidecharts_callbacks",
    "register_load_callbacks",
    "register_plot_callbacks",
#    "register_switch_callbacks",
    "register_sync_callbacks",
    "register_updatemenu_callbacks",
#    "register_jsonselect_callbacks",
]
